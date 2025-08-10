import sys
import asyncio, json, os, uuid, mimetypes, pathlib, time
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
        commands_to_try = [
            ['gemmit-npx', 'serve', '-p', str(port)],
            ['npx', 'serve', '-p', str(port)]
        ]
        
        for cmd in commands_to_try:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, cwd=str(work_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ
                )
                
                frontend_processes[port] = proc
                print(f"Started frontend server on port {port} in {work_dir} using {cmd[0]}")
                return True
                
            except FileNotFoundError:
                print(f"Command {cmd[0]} not found, trying next option...")
                continue
        
        print("No suitable serve command found (tried gemmit-npx and npx)", file=sys.stderr)
        return False
        
    except Exception as e:
        print(f"Failed to start frontend server: {e}", file=sys.stderr)
        return False

async def cancel_process(conversation_id: str):
    """Cancel a running gemini process"""
    if conversation_id in active_processes:
        try:
            proc = active_processes[conversation_id]
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        finally:
            active_processes.pop(conversation_id, None)
        return True
    return False

async def run_gemini(prompt: str, work_dir: pathlib.Path, ws, conversation_id: str):
    # Use chat endpoint, drop code-assist '-a'
    cmd = [GEMINI_BIN, '-y', '-a', '-p', prompt, '-m', 'gemini-2.5-flash']
    
    # Debug: Log the environment for MCP server debugging
    print(f"Running gemini-cli with PATH: {os.environ.get('PATH', 'NOT SET')}")
    print(f"Working directory: {work_dir}")
    print(f"Command: {' '.join(cmd)}")
    
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ  # Explicitly pass full environment for MCP server access
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
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
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
        
        # Handle process cancellation
        if command == 'cancel':
            cid = data.get('conversationId')
            if cid:
                success = await cancel_process(cid)
                await ws.send(json.dumps({
                    'type': 'cancel_result',
                    'success': success,
                    'conversationId': cid,
                    'message': f"Process {'cancelled' if success else 'not found or already completed'}"
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
        
        full_prompt = f"{prompt}\n\n[conversation history]\n{history}"
        rc, reply = await run_gemini(full_prompt, WORK_DIR, ws, cid)
        if rc == 0:
            conversations.setdefault(cid, []).extend([f"User: {prompt}", f"Model: {reply}"])
            # Persist conversations to disk
            save_conversations(conversations)
            print(f"Saved conversation {cid}, now has {len(conversations.get(cid, []))} messages", file=sys.stderr)
        
        # Send completion status
        await ws.send(json.dumps({'type': 'status', 'status': 'complete', 'conversationId': cid}))
        await ws.send(json.dumps({'type': 'result', 'returncode': rc, 'conversationId': cid}))

# Main entry point
async def main():
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT + 1)
    await site.start()
    ws_server = await websockets.serve(ws_handler, HOST, PORT)
    print(f"HTTP  at http://{HOST}:{PORT+1}  |  WS at ws://{HOST}:{PORT}")
    await ws_server.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())

