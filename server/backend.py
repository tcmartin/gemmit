import sys
import asyncio, json, os, uuid, mimetypes, pathlib, time, signal
import websockets
from aiohttp import web

# Determine base directory for static assets
if getattr(sys, "frozen", False):
    # PyInstaller extracts files to _MEIPASS
    BASE_DIR = pathlib.Path(sys._MEIPASS)
else:
    # Running in source, assume repo root
    BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

# Directories and config
home = pathlib.Path.home()
DEFAULT_PROJECTS = home / "Gemmit_Projects"
# Generation directory (where files are listed/read/written)
WORK_DIR = pathlib.Path(os.getenv('GENERATIONS_DIR', str(DEFAULT_PROJECTS)))
WORK_DIR.mkdir(parents=True, exist_ok=True)
# Output directory for any generated assets
OUTPUT_DIR = pathlib.Path(os.getenv('OUTPUT_DIR', str(DEFAULT_PROJECTS)))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Provision AI guidance docs into WORK_DIR/.gemmit ────────────
import sys, shutil


def _proc_group_kwargs():
    if os.name == 'posix':
        return {'preexec_fn': os.setsid}
    elif os.name == 'nt':
        # CREATE_NEW_PROCESS_GROUP
        return {'creationflags': 0x00000200}
    return {}

def provision_guidance_docs():
    """Provision AI guidance documents to the .gemmit directory and .geminiignore to WORK_DIR with proper error handling."""
    try:
        config_dir = WORK_DIR / ".gemmit"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if we have write permissions to the config directory
        if not os.access(config_dir, os.W_OK):
            print(f"Warning: No write permission to {config_dir}", file=sys.stderr)
            return
            
    except Exception as e:
        print(f"Warning: Could not create .gemmit directory: {e}", file=sys.stderr)
        return

    # Copy guidance documents to .gemmit directory
    for doc in ("ai_guidelines.md", "pocketflowguide.md"):
        src = BASE_DIR / doc
        dest = config_dir / doc
        
        # Skip if source doesn't exist
        if not src.exists():
            print(f"Warning: source file {src} not found", file=sys.stderr)
            continue
            
        # Check if we need to copy
        should_copy = False
        if not dest.exists():
            should_copy = True
        else:
            try:
                # Compare modification times
                if src.stat().st_mtime > dest.stat().st_mtime:
                    should_copy = True
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not check file times for {doc}: {e}", file=sys.stderr)
                # If we can't check times, assume we should copy
                should_copy = True
        
        if should_copy:
            try:
                # Use copy2 to preserve metadata, fallback to copy if that fails
                try:
                    shutil.copy2(src, dest)
                except (OSError, PermissionError):
                    shutil.copy(src, dest)
                print(f"Copied {doc} to .gemmit directory")
            except Exception as e:
                print(f"Warning: could not copy {src} → {dest}: {e}", file=sys.stderr)
                # On macOS, compiled apps might need special permissions
                if sys.platform == "darwin" and getattr(sys, "frozen", False):
                    print(f"Note: If running as compiled app on macOS, you may need to grant file access permissions", file=sys.stderr)

    # Copy .geminiignore directly to WORK_DIR (Gemmit_Projects folder)
    geminiignore_src = BASE_DIR / ".geminiignore"
    geminiignore_dest = WORK_DIR / ".geminiignore"
    
    if geminiignore_src.exists():
        should_copy_ignore = False
        if not geminiignore_dest.exists():
            should_copy_ignore = True
        else:
            try:
                # Compare modification times
                if geminiignore_src.stat().st_mtime > geminiignore_dest.stat().st_mtime:
                    should_copy_ignore = True
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not check file times for .geminiignore: {e}", file=sys.stderr)
                # If we can't check times, assume we should copy
                should_copy_ignore = True
        
        if should_copy_ignore:
            try:
                # Use copy2 to preserve metadata, fallback to copy if that fails
                try:
                    shutil.copy2(geminiignore_src, geminiignore_dest)
                except (OSError, PermissionError):
                    shutil.copy(geminiignore_src, geminiignore_dest)
                print(f"Copied .geminiignore to {WORK_DIR}")
            except Exception as e:
                print(f"Warning: could not copy .geminiignore to {WORK_DIR}: {e}", file=sys.stderr)
    else:
        print(f"Warning: .geminiignore source file not found at {geminiignore_src}", file=sys.stderr)

# Provision the guidance documents
provision_guidance_docs()

# Fallback: If files still don't exist, create minimal versions
def create_fallback_docs():
    """Create minimal fallback versions of guidance docs and .geminiignore if copying failed."""
    config_dir = WORK_DIR / ".gemmit"
    
    fallback_content = {
        "ai_guidelines.md": """# AI Guidelines
This file contains AI guidance for the project.
Note: This is a fallback version - the full guidelines may not have been copied.
""",
        "pocketflowguide.md": """# PocketFlow Guide
This file contains the PocketFlow development guide.
Note: This is a fallback version - the full guide may not have been copied.
"""
    }
    
    for doc, content in fallback_content.items():
        dest = config_dir / doc
        if not dest.exists():
            try:
                dest.write_text(content)
                print(f"Created fallback {doc}")
            except Exception as e:
                print(f"Warning: Could not create fallback {doc}: {e}", file=sys.stderr)

    # Create fallback .geminiignore in WORK_DIR if it doesn't exist
    geminiignore_dest = WORK_DIR / ".geminiignore"
    if not geminiignore_dest.exists():
        fallback_geminiignore = """# Gemini Ignore File
# This is a fallback .geminiignore - the full version may not have been copied.

# Common files to ignore
.DS_Store
Thumbs.db
.git/
node_modules/
__pycache__/
*.log
.env
.env.*
!.env.example
"""
        try:
            geminiignore_dest.write_text(fallback_geminiignore)
            print(f"Created fallback .geminiignore in {WORK_DIR}")
        except Exception as e:
            print(f"Warning: Could not create fallback .geminiignore: {e}", file=sys.stderr)

# Only create fallbacks if the main provisioning had issues
try:
    config_dir = WORK_DIR / ".gemmit"
    geminiignore_path = WORK_DIR / ".geminiignore"
    if (not (config_dir / "ai_guidelines.md").exists() or 
        not (config_dir / "pocketflowguide.md").exists() or 
        not geminiignore_path.exists()):
        create_fallback_docs()
except Exception:
    pass  # Silently fail fallback creation

def _resolve_target_dir(path_str: str, *, relative_to_current: bool = False) -> pathlib.Path:
    """
    Resolve the target directory from a user-supplied string.
    - Absolute stays absolute.
    - ~ expands to home.
    - Relative is interpreted relative to DEFAULT_PROJECTS by default,
      or relative to the CURRENT WORK_DIR if relative_to_current=True.
    """
    base = WORK_DIR if relative_to_current else DEFAULT_PROJECTS
    p = pathlib.Path(os.path.expanduser(path_str))
    if not p.is_absolute():
        p = base / p
    return p
def _ensure_geminiignore_in(dir_path: pathlib.Path) -> bool:
    """
    Ensure .geminiignore exists in dir_path.
    Returns True if we created/copied it, False if it already existed.
    """
    dest = dir_path / ".geminiignore"
    if dest.exists():
        return False

    src = BASE_DIR / ".geminiignore"
    try:
        if src.exists():
            try:
                shutil.copy2(src, dest)
            except (OSError, PermissionError):
                shutil.copy(src, dest)
        else:
            # Small, safe fallback so we never fail the op
            dest.write_text(
                "# Fallback .geminiignore\n"
                ".DS_Store\nThumbs.db\n.git/\nnode_modules/\n__pycache__/\n*.log\n.env\n.env.*\n!.env.example\n"
            )
        return True
    except Exception as e:
        print(f"Warning: Could not provision .geminiignore in {dir_path}: {e}", file=sys.stderr)
        return False


def _repoint_conversation_store(new_work_dir: pathlib.Path):
    """
    Update globals that depend on WORK_DIR and reload conversations for the new location.
    """
    global CONVERSATIONS_FILE, conversations
    CONVERSATIONS_FILE = new_work_dir / '.gemmit' / 'conversations.json'
    conversations = load_conversations()


def change_work_dir_sync(path_str: str, *, relative_to_current: bool = False, also_update_output_dir: bool = False):
    """
    Synchronous helper to switch WORK_DIR.
    - Creates the directory (and .gemmit) if missing.
    - Auto-provisions .geminiignore if absent.
    - Repoints conversations store.
    Returns dict with details for the UI.
    """
    global WORK_DIR, OUTPUT_DIR

    target = _resolve_target_dir(path_str, relative_to_current=relative_to_current)
    created = False
    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)
        created = True

    # Ensure per-project config dir exists
    (target / ".gemmit").mkdir(parents=True, exist_ok=True)

    # If the target doesn't have a .geminiignore, copy it in
    copied_ignore = _ensure_geminiignore_in(target)

    # Switch the active work dir
    WORK_DIR = target

    # Optionally keep OUTPUT_DIR in lockstep
    if also_update_output_dir:
        OUTPUT_DIR = target

    # Provision guidance docs (uses WORK_DIR), ignore errors
    try:
        provision_guidance_docs()
    except Exception as e:
        print(f"Warning: provision_guidance_docs() after dir change: {e}", file=sys.stderr)

    # Repoint conversation store for the new directory
    _repoint_conversation_store(WORK_DIR)

    return {
        "workDir": str(WORK_DIR),
        "created": created,
        "copiedGeminiignore": copied_ignore,
    }


GEMINI_BIN = os.getenv('GEMINI_PATH', 'gemini')
PORT = int(os.getenv('PORT', 8000))
HOST = os.getenv('HOST', '127.0.0.1')
HOST = os.getenv('HOST', '127.0.0.1')

# Persistent conversation storage
CONVERSATIONS_FILE = WORK_DIR / '.gemmit' / 'conversations.json'

def load_conversations():
    """Load conversations from persistent storage."""
    if CONVERSATIONS_FILE.exists():
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, PermissionError, OSError) as e:
            print(f"Warning: Could not load conversations: {e}", file=sys.stderr)
    return {}

def save_conversations(conversations):
    """Save conversations to persistent storage."""
    try:
        CONVERSATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)
    except (PermissionError, OSError) as e:
        print(f"Warning: Could not save conversations: {e}", file=sys.stderr)

# Load conversations on startup
conversations: dict[str, list[str]] = load_conversations()
startup_time = time.time()
print(f"Backend started at {time.ctime(startup_time)}, loaded {len(conversations)} conversations", file=sys.stderr)

# Process tracking for cancellation
active_processes: dict[str, asyncio.subprocess.Process] = {}
active_tasks: dict[str, asyncio.Task] = {}  # Track the actual tasks for cancellation
frontend_processes: dict[int, asyncio.subprocess.Process] = {}

# HTTP server: static files and health endpoint
STATIC_ROOT = BASE_DIR / 'app'

async def health(request):
    return web.Response(text='ok')

@web.middleware
async def spa_fallback(request, handler):
    try:
        return await handler(request)
    except web.HTTPNotFound:
        # Serve index.html for SPA routing
        return web.FileResponse(STATIC_ROOT / 'index.html')

app = web.Application(middlewares=[spa_fallback])
app.router.add_get('/health', health)
app.router.add_static('/', STATIC_ROOT, show_index=True)

# WebSocket handler and streaming utilities
async def stream_pipe(pipe, name, ws, buffer):
    try:
        while True:
            chunk = await pipe.readline()
            if not chunk:
                break
            data = chunk.decode()
            if name == 'stdout':
                buffer.append(data)
            await ws.send(json.dumps({'type': 'stream', 'stream': name, 'data': data}))
    except asyncio.CancelledError:
        # Stream was cancelled, this is expected
        raise
    except Exception as e:
        # Handle other errors gracefully
        print(f"Error in stream_pipe: {e}", file=sys.stderr)

async def monitor_frontend_process(port: int, proc: asyncio.subprocess.Process):
    """Monitor a frontend process and clean up when it exits"""
    try:
        await proc.wait()
        print(f"Frontend server on port {port} exited with code {proc.returncode}", file=sys.stderr)
        if proc.returncode != 0:
            stdout, stderr = await proc.communicate()
            print(f"Frontend server error output:", file=sys.stderr)
            print(f"stdout: {stdout.decode()}", file=sys.stderr)
            print(f"stderr: {stderr.decode()}", file=sys.stderr)
    except Exception as e:
        print(f"Error monitoring frontend process on port {port}: {e}", file=sys.stderr)
    finally:
        frontend_processes.pop(port, None)

async def stop_frontend_server(port: int):
    """Stop a frontend server running on the specified port"""
    if port in frontend_processes:
        try:
            proc = frontend_processes[port]
            print(f"Stopping frontend server on port {port}", file=sys.stderr)
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
                print(f"Frontend server on port {port} stopped gracefully", file=sys.stderr)
            except asyncio.TimeoutError:
                print(f"Frontend server on port {port} didn't stop gracefully, killing", file=sys.stderr)
                proc.kill()
                await proc.wait()
            return True
        except Exception as e:
            print(f"Error stopping frontend server on port {port}: {e}", file=sys.stderr)
            return False
        finally:
            frontend_processes.pop(port, None)
    else:
        print(f"No frontend server running on port {port}", file=sys.stderr)
        return False

async def start_frontend_server(port: int, work_dir: pathlib.Path):
    """Start a frontend server using npx serve (or gemmit-npx in production)"""
    try:
        # Kill existing server on this port if it exists
        if port in frontend_processes:
            try:
                frontend_processes[port].terminate()
                await asyncio.wait_for(frontend_processes[port].wait(), timeout=5.0)
            except asyncio.TimeoutError:
                frontend_processes[port].kill()
                await frontend_processes[port].wait()
            finally:
                del frontend_processes[port]
        
        # Try gemmit-npx first (for production), fallback to npx (for development)
        # Use -C for CORS, -L to disable request logging for cleaner output
        # Removed -s flag as it interferes with serving multiple HTML files
        # Removed --no-etag as it's not supported in all versions
        commands_to_try = [
            ['gemmit-npx', 'serve', '-C', '-L', '-p', str(port)],
            ['npx', 'serve', '-C', '-L', '-p', str(port)],
            # Fallback without CORS if that fails
            ['gemmit-npx', 'serve', '-p', str(port)],
            ['npx', 'serve', '-p', str(port)],
            # Ultimate fallback: Python's built-in HTTP server
            ['python3', '-m', 'http.server', str(port)],
            ['python', '-m', 'http.server', str(port)]
        ]
        
        for cmd in commands_to_try:
            try:
                print(f"Attempting to start server with command: {' '.join(cmd)}", file=sys.stderr)
                proc = await asyncio.create_subprocess_exec(
                    *cmd, cwd=str(work_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ
                )
                
                # Wait a moment to see if the process starts successfully
                await asyncio.sleep(1.0)
                
                # Check if process is still running
                if proc.returncode is None:
                    frontend_processes[port] = proc
                    print(f"Started frontend server on port {port} in {work_dir} using {cmd[0]}")
                    
                    # Start a task to monitor the process
                    asyncio.create_task(monitor_frontend_process(port, proc))
                    
                    # Wait a bit more and test if the server is actually responding
                    await asyncio.sleep(1.0)
                    
                    # Try to connect to the server to verify it's working
                    try:
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            # Test both root and a specific HTML file
                            test_urls = [f'http://localhost:{port}', f'http://localhost:{port}/index.html']
                            
                            for test_url in test_urls:
                                try:
                                    async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=3)) as response:
                                        content_type = response.headers.get('content-type', 'unknown')
                                        print(f"✅ {test_url} -> Status: {response.status}, Content-Type: {content_type}", file=sys.stderr)
                                        
                                        if response.status < 500:
                                            # Read a bit of content to verify it's actually HTML
                                            if test_url.endswith('.html') or test_url.endswith('/'):
                                                content_preview = await response.text()
                                                if content_preview.strip().startswith('<!DOCTYPE') or content_preview.strip().startswith('<html'):
                                                    print(f"✅ HTML content verified for {test_url}", file=sys.stderr)
                                                else:
                                                    print(f"⚠️ Unexpected content for {test_url}: {content_preview[:100]}...", file=sys.stderr)
                                except Exception as url_e:
                                    print(f"⚠️ Could not test {test_url}: {url_e}", file=sys.stderr)
                            
                            return True
                    except Exception as e:
                        print(f"⚠️ Could not verify server on port {port}: {e}", file=sys.stderr)
                        # Still return True since the process is running
                        return True
                else:
                    # Process exited immediately, read error output
                    stdout, stderr = await proc.communicate()
                    print(f"Command {cmd[0]} failed immediately:", file=sys.stderr)
                    print(f"stdout: {stdout.decode()}", file=sys.stderr)
                    print(f"stderr: {stderr.decode()}", file=sys.stderr)
                    continue
                
            except FileNotFoundError:
                print(f"Command {cmd[0]} not found, trying next option...")
                continue
            except Exception as e:
                print(f"Error starting {cmd[0]}: {e}", file=sys.stderr)
                continue
        
        print("No suitable serve command found (tried gemmit-npx and npx)", file=sys.stderr)
        return False
        
    except Exception as e:
        print(f"Failed to start frontend server: {e}", file=sys.stderr)
        return False

async def cancel_process(conversation_id: str):
    """Cancel a running gemini process (equivalent to Ctrl+C)"""
    success = False
    
    print(f"🛑 CANCEL REQUEST: {conversation_id}", file=sys.stderr)
    print(f"Active tasks: {list(active_tasks.keys())}", file=sys.stderr)
    print(f"Active processes: {list(active_processes.keys())}", file=sys.stderr)
    
    # Cancel the asyncio task FIRST - this is more immediate
    if conversation_id in active_tasks:
        try:
            task = active_tasks[conversation_id]
            print(f"🛑 Cancelling task for conversation {conversation_id}", file=sys.stderr)
            task.cancel()
            
            # Wait a very short time for the task to actually cancel
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass  # Expected when task is cancelled
            
            success = True
            print(f"✅ Task cancelled for {conversation_id}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Error cancelling task {conversation_id}: {e}", file=sys.stderr)
    
    # Also kill the process directly (belt and suspenders approach)
    if conversation_id in active_processes:
        try:
            proc = active_processes[conversation_id]
            print(f"🛑 Force killing process for conversation {conversation_id} (PID: {proc.pid})", file=sys.stderr)

            # TERM first
            try:
                if os.name == 'posix':
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=1.0)
                print(f"✅ Process {conversation_id} terminated gracefully", file=sys.stderr)
            except asyncio.TimeoutError:
                print(f"🛑 TERM timeout, escalating for {conversation_id}", file=sys.stderr)
                if os.name == 'posix':
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                    print(f"✅ Process {conversation_id} killed immediately", file=sys.stderr)
                except asyncio.TimeoutError:
                    print(f"⚠️ Process {conversation_id} didn't die after SIGKILL", file=sys.stderr)
            success = True
        except Exception as e:
            print(f"❌ Error killing process {conversation_id}: {e}", file=sys.stderr)
        finally:
            active_processes.pop(conversation_id, None)
    
    # Clean up task tracking immediately
    active_tasks.pop(conversation_id, None)
    
    if not success:
        print(f"❌ No active task or process found for conversation {conversation_id}", file=sys.stderr)
    else:
        print(f"✅ Successfully cancelled conversation {conversation_id}", file=sys.stderr)
    
    return success

async def run_gemini(prompt: str, work_dir: pathlib.Path, ws, conversation_id: str):
    # Use chat endpoint, drop code-assist '-a'
    cmd = [GEMINI_BIN, '-y', '-a', '-p', prompt, '-m', 'gemini-2.5-flash']
    
    # Create process in new process group for proper signal handling
    # Ensure MCP servers can access the full environment including embedded node runtime
    gemini_env = os.environ.copy()
    
    # Ensure critical environment variables are set for MCP server access
    if 'HOME' not in gemini_env:
        gemini_env['HOME'] = str(pathlib.Path.home())
    
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=gemini_env,
        **_proc_group_kwargs(),
    )
    
    # Track the process for cancellation
    active_processes[conversation_id] = proc
    
    try:
        out_buf: list[str] = []
        await asyncio.gather(
            stream_pipe(proc.stdout, 'stdout', ws, out_buf),
            stream_pipe(proc.stderr, 'stderr', ws, [])
        )
        await proc.wait()
        return proc.returncode, ''.join(out_buf)
    except asyncio.CancelledError:
        print(f"Process {conversation_id} was cancelled, terminating...", file=sys.stderr)
        try:
            if os.name == 'posix':
                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
            else:
                # Requires creationflags=CREATE_NEW_PROCESS_GROUP
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            try:
                if os.name == 'posix':
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                if os.name == 'posix':
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
                await proc.wait()
        except Exception as e:
            print(f"Error during cancellation: {e}", file=sys.stderr)

        try:
            await ws.send(json.dumps({'type': 'stream', 'stream': 'stderr', 'data': '\n[Process cancelled by user]\n'}))
        except Exception:
            pass  # WS may be closed
        return -1, '[Process cancelled by user]'
    finally:
        # Clean up process tracking
        active_processes.pop(conversation_id, None)

async def ws_handler(ws, path=None):
    async for msg in ws:
        data = json.loads(msg)
        # File operations
        typ = data.get('type')
        if typ == 'list_files':
            files = [f.name for f in WORK_DIR.iterdir() if f.is_file()]
            await ws.send(json.dumps({'type': 'file_list', 'files': files}))
            continue
        if typ == 'get_file':
            fn = WORK_DIR / data['filename']
            try:
                content = fn.read_text()
                err = ''
            except Exception as e:
                content, err = '', str(e)
            await ws.send(json.dumps({'type': 'file_content', 'filename': fn.name, 'content': content, 'error': err}))
            continue
        if typ == 'save_file':
            fn = WORK_DIR / data['filename']
            try:
                fn.write_text(data['content'])
                err = ''
            except Exception as e:
                err = str(e)
            await ws.send(json.dumps({'type': 'save_ack', 'filename': fn.name, 'error': err}))
            continue
        
        # Handle frontend server commands
        command = data.get('command')
        if command == 'start-frontend':
            port = int(data.get('port', 5002))
            success = await start_frontend_server(port, WORK_DIR)
            await ws.send(json.dumps({
                'type': 'frontend_result', 
                'success': success, 
                'port': port,
                'message': f"Frontend server {'started' if success else 'failed to start'} on port {port}"
            }))
            continue
        if command == 'change-workdir':
            # Accept: path (str), relativeToCurrent (bool), alsoUpdateOutputDir (bool)
            path_str = data.get('path') or data.get('dir') or data.get('workDir')
            relative_to_current = bool(data.get('relativeToCurrent', False))
            also_update_output_dir = bool(data.get('alsoUpdateOutputDir', False))

            if not path_str:
                await ws.send(json.dumps({
                    'type': 'workdir_result',
                    'success': False,
                    'error': 'Missing "path"'
                }))
                continue

            # Optional: let the user know if processes are running
            has_active = bool(active_tasks or active_processes)

            try:
                info = change_work_dir_sync(
                    path_str,
                    relative_to_current=relative_to_current,
                    also_update_output_dir=also_update_output_dir
                )
                await ws.send(json.dumps({
                    'type': 'workdir_result',
                    'success': True,
                    'hasActiveTasks': has_active,
                    **info
                }))
            except Exception as e:
                await ws.send(json.dumps({
                    'type': 'workdir_result',
                    'success': False,
                    'error': str(e)
                }))
            continue
        
        if command == 'stop-frontend':
            port = int(data.get('port', 5002))
            success = await stop_frontend_server(port)
            await ws.send(json.dumps({
                'type': 'frontend_result',
                'success': success,
                'port': port,
                'message': f"Frontend server {'stopped' if success else 'not running or failed to stop'} on port {port}"
            }))
            continue
        
        # Handle process cancellation
        if command == 'cancel':
            cid = data.get('conversationId')
            if cid:
                print(f"Attempting to cancel process for conversation {cid}", file=sys.stderr)
                success = await cancel_process(cid)
                
                # Always report success to user for immediate feedback
                # Even if process already completed, user gets confirmation
                message = f"Cancellation request processed"
                if success:
                    message = f"Process cancelled successfully"
                else:
                    message = f"Process already completed or not found"
                    
                print(f"Cancel result: {message}", file=sys.stderr)
                await ws.send(json.dumps({
                    'type': 'cancel_result',
                    'success': True,  # Always true for UI feedback
                    'conversationId': cid,
                    'message': message
                }))
            continue
        
        # Handle status check
        if command == 'status':
            await ws.send(json.dumps({
                'type': 'status_info',
                'active_processes': list(active_processes.keys()),
                'active_tasks': list(active_tasks.keys()),
                'frontend_processes': list(frontend_processes.keys())
            }))
            continue
        
        # Handle conversation list request
        if command == 'list-conversations':
            conversation_list = []
            for cid, messages in conversations.items():
                if messages:  # Only include conversations with messages
                    # Get the first user message as preview
                    first_message = messages[0] if messages else ""
                    preview = first_message.replace("User: ", "").strip()[:100]
                    if len(preview) > 100:
                        preview += "..."
                    
                    conversation_list.append({
                        'id': cid,
                        'preview': preview,
                        'messageCount': len(messages),
                        'lastModified': time.time()  # We don't track this yet, so use current time
                    })
            
            # Sort by message count (most recent activity first)
            conversation_list.sort(key=lambda x: x['messageCount'], reverse=True)
            
            await ws.send(json.dumps({
                'type': 'conversation_list',
                'conversations': conversation_list
            }))
            continue
        
        # Handle conversation load request
        if command == 'load-conversation':
            target_cid = data.get('conversationId')
            if target_cid and target_cid in conversations:
                await ws.send(json.dumps({
                    'type': 'conversation_loaded',
                    'conversationId': target_cid,
                    'messages': conversations[target_cid]
                }))
            else:
                await ws.send(json.dumps({
                    'type': 'conversation_loaded',
                    'conversationId': target_cid,
                    'messages': [],
                    'error': 'Conversation not found'
                }))
            continue
        
        # Conversation prompt
       # Conversation prompt
        prompt = data.get('prompt')
        cid = data.get('conversationId') or str(uuid.uuid4())
        if not prompt:
            await ws.send(json.dumps({'error': 'prompt missing'}))
            continue

        print(f"Processing prompt for conversation {cid}, current conversations count: {len(conversations)}", file=sys.stderr)
        history = '\n'.join(conversations.get(cid, []))
        print(f"Conversation {cid} has {len(conversations.get(cid, []))} previous messages", file=sys.stderr)

        # Tell the UI we started
        await ws.send(json.dumps({'type': 'status', 'status': 'running', 'conversationId': cid}))

        # Prepare the full prompt for the worker
        full_prompt = f"{prompt}\n\n[conversation history]\n{history}"

        async def run_gemini_task():
            return await run_gemini(full_prompt, WORK_DIR, ws, cid)

        # START the task, but DO NOT AWAIT IT here (keep the WS loop responsive).
        task = asyncio.create_task(run_gemini_task())
        active_tasks[cid] = task

        async def _finalize(t: asyncio.Task, _cid=cid, _prompt=prompt):
            rc, reply = -1, ""
            try:
                rc, reply = await t
                if rc == 0:
                    conversations.setdefault(_cid, []).extend([f"User: {_prompt}", f"Model: {reply}"])
                    save_conversations(conversations)
                    print(f"Saved conversation {_cid}, now has {len(conversations.get(_cid, []))} messages", file=sys.stderr)
            except asyncio.CancelledError:
                rc, reply = -1, "[Cancelled by user]"
                try:
                    await ws.send(json.dumps({'type': 'stream', 'stream': 'stderr', 'data': '\n[Cancelled by user]\n'}))
                except Exception:
                    pass  # WS may be closed
            finally:
                active_tasks.pop(_cid, None)
                try:
                    await ws.send(json.dumps({'type': 'status', 'status': 'complete', 'conversationId': _cid}))
                    await ws.send(json.dumps({'type': 'result', 'returncode': rc, 'conversationId': _cid}))
                except Exception:
                    pass  # WS may be closed

        asyncio.create_task(_finalize(task))
        # Loop continues WITHOUT awaiting the task; we can now receive 'cancel' immediately.
async def cleanup_processes():
    """Clean up all running processes"""
    print("Cleaning up processes...", file=sys.stderr)
    
    # Cancel all active tasks
    for cid, task in list(active_tasks.items()):
        try:
            task.cancel()
            await asyncio.sleep(0.1)  # Give tasks a moment to cancel
        except Exception as e:
            print(f"Error cancelling task {cid}: {e}", file=sys.stderr)
    
    # Kill all active gemini processes
    for cid, proc in list(active_processes.items()):
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        except Exception as e:
            print(f"Error cleaning up process {cid}: {e}", file=sys.stderr)
    
    # Kill all frontend processes
    for port, proc in list(frontend_processes.items()):
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        except Exception as e:
            print(f"Error cleaning up frontend process on port {port}: {e}", file=sys.stderr)
    
    print("Process cleanup complete", file=sys.stderr)

# Main entry point
async def main():
    import signal
    
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down...", file=sys.stderr)
        # Create a task to cleanup processes
        asyncio.create_task(cleanup_processes())
        # Exit after cleanup
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, HOST, PORT + 1)
        await site.start()
        ws_server = await websockets.serve(ws_handler, HOST, PORT)
        print(f"HTTP  at http://{HOST}:{PORT+1}  |  WS at ws://{HOST}:{PORT}")
        await ws_server.wait_closed()
    except KeyboardInterrupt:
        print("Keyboard interrupt received", file=sys.stderr)
    finally:
        await cleanup_processes()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Backend shutting down...", file=sys.stderr)

