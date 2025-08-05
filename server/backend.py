import asyncio, json, os, uuid, mimetypes, pathlib
import websockets, aiohttp.web

WORK_DIR = pathlib.Path(os.getenv('GENERATIONS_DIR', os.getcwd()))
OUTPUT_DIR = pathlib.Path(os.getenv('OUTPUT_DIR', os.getcwd()))
GEMINI_BIN = os.getenv('GEMINI_PATH', 'gemini')
PORT = int(os.getenv('PORT', 8000))
HOST = os.getenv('HOST', '127.0.0.1')

conversations: dict[str, list[str]] = {}

# ---------- HTTP server (static + /health) -----------------
STATIC_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"

async def health(_):
    return aiohttp.web.Response(text="ok")

@aiohttp.web.middleware
async def spa(_, handler):
    try:
        return await handler(_)
    except aiohttp.web.HTTPNotFound:
        # fallback to index.html (single-page-app)
        return aiohttp.web.FileResponse(STATIC_ROOT / "index.html")

app = aiohttp.web.Application(middlewares=[spa])
app.add_routes([
    aiohttp.web.get('/health', health),
    aiohttp.web.static('/', STATIC_ROOT, show_index=True),
])

# ---------- WebSocket handler --------------------------------
async def stream_pipe(pipe, name, ws, buf):
    while (chunk := await pipe.readline()):
        chunk = chunk.decode()
        if name == 'stdout': buf.append(chunk)
        await ws.send(json.dumps({'type': 'stream', 'stream': name, 'data': chunk}))

async def run_gemini(prompt, work_dir, ws):
    cmd = [
        GEMINI_BIN, '-y', '-a',
        '-p', prompt,
        '-m', 'gemini-2.5-flash'
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=work_dir,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    buf: list[str] = []
    await asyncio.gather(
        stream_pipe(proc.stdout, 'stdout', ws, buf),
        stream_pipe(proc.stderr, 'stderr', ws, [])
    )
    await proc.wait()
    return proc.returncode, ''.join(buf)

async def ws_handler(ws, path=None):
    async for msg in ws:
        data = json.loads(msg)
        # -------- file ops ----------
        if data.get('type') == 'list_files':
            files = [f.name for f in WORK_DIR.iterdir() if f.is_file()]
            await ws.send(json.dumps({'type': 'file_list', 'files': files}))
            continue
        if data.get('type') == 'get_file':
            fp = WORK_DIR / data['filename']
            try:
                content = fp.read_text()
            except Exception as e:
                content, err = '', str(e)
            else:
                err = ''
            await ws.send(json.dumps({'type': 'file_content', 'filename': fp.name,
                                      'content': content, 'error': err}))
            continue
        if data.get('type') == 'save_file':
            fp = WORK_DIR / data['filename']
            try:
                fp.write_text(data['content'])
                err = ''
            except Exception as e:
                err = str(e)
            await ws.send(json.dumps({'type': 'save_ack', 'filename': fp.name, 'error': err}))
            continue

        # -------- prompt ----------
        prompt, cid = data.get('prompt'), data.get('conversationId') or str(uuid.uuid4())
        if not prompt:
            await ws.send(json.dumps({'error': 'prompt missing'}))
            continue

        history = '\n'.join(conversations.get(cid, []))
        full_prompt = f"{prompt}\n\n[conversation history]\n{history}"
        rc, reply = await run_gemini(full_prompt, WORK_DIR, ws)
        if rc == 0:
            conversations.setdefault(cid, []).extend([f"User: {prompt}", f"Model: {reply}"])
        await ws.send(json.dumps({'type': 'result', 'returncode': rc, 'conversationId': cid}))

# --- bottom of backend.py ----------------------------------------------------
async def main():
    # ---------- start HTTP (static + /health) -------------------------------
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, HOST, PORT + 1)
    await site.start()

    # ---------- start WebSocket server --------------------------------------
    ws_server = await websockets.serve(ws_handler, HOST, PORT)

    print(f"HTTP  at http://{HOST}:{PORT+1}  |  WS at ws://{HOST}:{PORT}")
    # Block forever until the WS server closes (Ctrl-C etc.)
    await ws_server.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
