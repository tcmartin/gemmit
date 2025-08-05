import sys
import asyncio, json, os, uuid, mimetypes, pathlib
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
    """Provision AI guidance documents to the .gemmit directory with proper error handling."""
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

# Provision the guidance documents
provision_guidance_docs()

# Fallback: If files still don't exist, create minimal versions
def create_fallback_docs():
    """Create minimal fallback versions of guidance docs if copying failed."""
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

# Only create fallbacks if the main provisioning had issues
try:
    config_dir = WORK_DIR / ".gemmit"
    if not (config_dir / "ai_guidelines.md").exists() or not (config_dir / "pocketflowguide.md").exists():
        create_fallback_docs()
except Exception:
    pass  # Silently fail fallback creation


GEMINI_BIN = os.getenv('GEMINI_PATH', 'gemini')
PORT = int(os.getenv('PORT', 8000))
HOST = os.getenv('HOST', '127.0.0.1')
HOST = os.getenv('HOST', '127.0.0.1')

# In-memory conversation storage
conversations: dict[str, list[str]] = {}

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
    while True:
        chunk = await pipe.readline()
        if not chunk:
            break
        data = chunk.decode()
        if name == 'stdout':
            buffer.append(data)
        await ws.send(json.dumps({'type': 'stream', 'stream': name, 'data': data}))

async def run_gemini(prompt: str, work_dir: pathlib.Path, ws):
    # Use chat endpoint, drop code-assist '-a'
    cmd = [GEMINI_BIN, '-y', '-a', '-p', prompt, '-m', 'gemini-2.5-flash']
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=str(work_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    out_buf: list[str] = []
    await asyncio.gather(
        stream_pipe(proc.stdout, 'stdout', ws, out_buf),
        stream_pipe(proc.stderr, 'stderr', ws, [])
    )
    await proc.wait()
    return proc.returncode, ''.join(out_buf)

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
        # Conversation prompt
        prompt = data.get('prompt')
        cid = data.get('conversationId') or str(uuid.uuid4())
        if not prompt:
            await ws.send(json.dumps({'error': 'prompt missing'}))
            continue
        history = '\n'.join(conversations.get(cid, []))
        full_prompt = f"{prompt}\n\n[conversation history]\n{history}"
        rc, reply = await run_gemini(full_prompt, WORK_DIR, ws)
        if rc == 0:
            conversations.setdefault(cid, []).extend([f"User: {prompt}", f"Model: {reply}"])
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

