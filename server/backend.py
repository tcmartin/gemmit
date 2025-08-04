import asyncio
import json
import os
import websockets
import uuid

# In-memory storage for conversations
default_output_dir = os.getenv('OUTPUT_DIR', os.getcwd())
conversations = {}

async def stream_pipe(pipe, stream_name, websocket, output_buffer):
    """Reads from a stream and sends data to the websocket."""
    while True:
        line = await pipe.readline()
        if not line:
            break
        decoded_line = line.decode()
        if stream_name == 'stdout':
            output_buffer.append(decoded_line)
        await websocket.send(json.dumps({'type': 'stream', 'stream': stream_name, 'data': decoded_line}))

async def stream_command_output(process, websocket):
    """Streams stdout and stderr from a process to the websocket."""
    output_buffer = []
    await asyncio.gather(
        stream_pipe(process.stdout, 'stdout', websocket, output_buffer),
        stream_pipe(process.stderr, 'stderr', websocket, [])
    )
    return ''.join(output_buffer)

async def handler(websocket, path):
    """Handles websocket connections, file ops, commands, and conversation prompts."""
    try:
        async for message in websocket:
            data = json.loads(message)
            # -- File operations --
            action = data.get('type')
            work_dir = os.getenv('GENERATIONS_DIR', default_output_dir)
            if action == 'list_files':
                try:
                    files = os.listdir(work_dir)
                except Exception as e:
                    files = []
                await websocket.send(json.dumps({'type': 'file_list', 'files': files}))
                continue
            if action == 'get_file':
                filename = data.get('filename')
                path = os.path.join(work_dir, filename)
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                    await websocket.send(json.dumps({'type': 'file_content', 'filename': filename, 'content': content}))
                except Exception as e:
                    await websocket.send(json.dumps({'type': 'file_content', 'filename': filename, 'content': '', 'error': str(e)}))
                continue
            if action == 'save_file':
                filename = data.get('filename')
                content = data.get('content')
                path = os.path.join(work_dir, filename)
                try:
                    with open(path, 'w') as f:
                        f.write(content)
                    await websocket.send(json.dumps({'type': 'save_success', 'filename': filename}))
                except Exception as e:
                    await websocket.send(json.dumps({'type': 'save_error', 'filename': filename, 'error': str(e)}))
                continue

            # -- Frontend command --
            cmd = data.get('command')
            if cmd == 'start-frontend':
                port = data.get('port')
                # Example: spawn your frontend dev server
                asyncio.create_subprocess_exec('npm', 'run', 'dev', '--', '--port', str(port), cwd=work_dir)
                await websocket.send(json.dumps({'type': 'start_frontend_ack', 'status': 'started', 'port': port}))
                continue

            # -- Conversation prompt handling --
            prompt = data.get('prompt')
            conversation_id = data.get('conversationId')
            if not prompt:
                await websocket.send(json.dumps({'error': 'Prompt not provided'}))
                continue
            if conversation_id not in conversations:
                conversations[conversation_id] = []
                print(f"New conversation started: {conversation_id}")

            history = "\n".join(conversations[conversation_id])
            full_prompt = f"{prompt}\n\n[conversation history]\n{history}"

            work_dir = os.getenv('GENERATIONS_DIR', default_output_dir)
            gemini_path = os.getenv('GEMINI_PATH', 'gemini')
            command = [
                gemini_path,
                '-y', '-a',
                '-p', full_prompt,
                '-m', 'gemini-2.5-flash'
            ]

            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            model_response = await stream_command_output(process, websocket)
            await process.wait()

            if process.returncode == 0:
                conversations[conversation_id].extend([
                    f"User: {prompt}",
                    f"Model: {model_response}"
                ])

            await websocket.send(json.dumps({'type': 'result', 'returncode': process.returncode}))

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for conversation: {conversation_id}")
    except Exception as e:
        print(f"Error in handler: {e}")

async def main():
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    async with websockets.serve(handler, host, port):
        print(f"WebSocket server started at ws://{host}:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
