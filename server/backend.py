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
    
    # Cancel the asyncio task first
    if conversation_id in active_tasks:
        try:
            task = active_tasks[conversation_id]
            print(f"Cancelling task for conversation {conversation_id}", file=sys.stderr)
            task.cancel()
            success = True
        except Exception as e:
            print(f"Error cancelling task {conversation_id}: {e}", file=sys.stderr)
    
    # Also try to kill the process directly
    if conversation_id in active_processes:
        try:
            proc = active_processes[conversation_id]
            print(f"Sending SIGINT to process {conversation_id}", file=sys.stderr)
            # Send SIGINT first (equivalent to Ctrl+C)
            proc.send_signal(signal.SIGINT)
            try:
                await asyncio.wait_for(proc.wait(), timeout=1.0)
                print(f"Process {conversation_id} terminated with SIGINT", file=sys.stderr)
            except asyncio.TimeoutError:
                print(f"SIGINT timeout, sending SIGTERM to {conversation_id}", file=sys.stderr)
                # If SIGINT doesn't work, try SIGTERM
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=1.0)
                    print(f"Process {conversation_id} terminated with SIGTERM", file=sys.stderr)
                except asyncio.TimeoutError:
                    print(f"SIGTERM timeout, sending SIGKILL to {conversation_id}", file=sys.stderr)
                    # Last resort: SIGKILL
                    proc.kill()
                    await proc.wait()
                    print(f"Process {conversation_id} killed with SIGKILL", file=sys.stderr)
            success = True
        except Exception as e:
            print(f"Error cancelling process {conversation_id}: {e}", file=sys.stderr)
        finally:
            active_processes.pop(conversation_id, None)
    
    # Clean up task tracking
    active_tasks.pop(conversation_id, None)
    
    return success

async def run_gemini(prompt: str, work_dir: pathlib.Path, ws, conversation_id: str):
    # Use chat endpoint, drop code-assist '-a'
    cmd = [GEMINI_BIN, '-y', '-a', '-p', prompt, '-m', 'gemini-2.5-flash']
    
    # Debug: Log the environment for MCP server debugging
    print(f"Running gemini-cli with PATH: {os.environ.get('PATH', 'NOT SET')}")
    print(f"Working directory: {work_dir}")
    print(f"Command: {' '.join(cmd)}")
    
    # Create process in new process group for proper signal handling
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ,  # Explicitly pass full environment for MCP server access
        preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create new process group on Unix
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
        # Process was cancelled
        print(f"Process {conversation_id} was cancelled, terminating...", file=sys.stderr)
        try:
            # Send SIGINT first (like Ctrl+C)
            proc.send_signal(signal.SIGINT)
            await asyncio.wait_for(proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            print(f"SIGINT timeout, sending SIGTERM to {conversation_id}", file=sys.stderr)
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                print(f"SIGTERM timeout, sending SIGKILL to {conversation_id}", file=sys.stderr)
                proc.kill()
                await proc.wait()
        except Exception as e:
            print(f"Error during cancellation: {e}", file=sys.stderr)
        
        await ws.send(json.dumps({'type': 'stream', 'stream': 'stderr', 'data': '\n[Process cancelled by user]\n'}))
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
                message = f"Process {'cancelled' if success else 'not found or already completed'}"
                print(f"Cancel result: {message}", file=sys.stderr)
                await ws.send(json.dumps({
                    'type': 'cancel_result',
                    'success': success,
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
        
        # Conversation prompt
        prompt = data.get('prompt')
        cid = data.get('conversationId') or str(uuid.uuid4())
        if not prompt:
            await ws.send(json.dumps({'error': 'prompt missing'}))
            continue
        
        print(f"Processing prompt for conversation {cid}, current conversations count: {len(conversations)}", file=sys.stderr)
        history = '\n'.join(conversations.get(cid, []))
        print(f"Conversation {cid} has {len(conversations.get(cid, []))} previous messages", file=sys.stderr)
        
        # Send status update
        await ws.send(json.dumps({'type': 'status', 'status': 'running', 'conversationId': cid}))
        
        # Create and track the task for cancellation
        full_prompt = f"{prompt}\n\n[conversation history]\n{history}"
        
        async def run_gemini_task():
            return await run_gemini(full_prompt, WORK_DIR, ws, cid)
        
        task = asyncio.create_task(run_gemini_task())
        active_tasks[cid] = task
        
        try:
            rc, reply = await task
            if rc == 0:
                conversations.setdefault(cid, []).extend([f"User: {prompt}", f"Model: {reply}"])
                # Persist conversations to disk
                save_conversations(conversations)
                print(f"Saved conversation {cid}, now has {len(conversations.get(cid, []))} messages", file=sys.stderr)
        except asyncio.CancelledError:
            print(f"Task for conversation {cid} was cancelled", file=sys.stderr)
            rc, reply = -1, "[Cancelled by user]"
            await ws.send(json.dumps({'type': 'stream', 'stream': 'stderr', 'data': '\n[Cancelled by user]\n'}))
        finally:
            # Clean up task tracking
            active_tasks.pop(cid, None)
        
        # Send completion status
        await ws.send(json.dumps({'type': 'status', 'status': 'complete', 'conversationId': cid}))
        await ws.send(json.dumps({'type': 'result', 'returncode': rc, 'conversationId': cid}))

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

