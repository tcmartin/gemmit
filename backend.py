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
        try:
            line = await pipe.readline()
            if not line:
                break
            decoded_line = line.decode()
            if stream_name == 'stdout':
                output_buffer.append(decoded_line)
            response = {'type': 'stream', 'stream': stream_name, 'data': decoded_line}
            await websocket.send(json.dumps(response))
        except Exception as e:
            print(f"Error streaming {stream_name}: {e}")
            break

async def stream_command_output(process, websocket):
    """Streams stdout and stderr from a process to the websocket."""
    output_buffer = []
    await asyncio.gather(
        stream_pipe(process.stdout, 'stdout', websocket, output_buffer),
        stream_pipe(process.stderr, 'stderr', websocket, [])
    )
    return ''.join(output_buffer)

async def handler(websocket, path):
    """Handles websocket connections and conversations."""
    try:
        async for message in websocket:
            data = json.loads(message)
            prompt = data.get('prompt')
            conversation_id = data.get('conversationId')

            if conversation_id not in conversations:
                conversations[conversation_id] = []
                print(f"New conversation started: {conversation_id}")

            if not prompt:
                await websocket.send(json.dumps({'error': 'Prompt not provided'}))
                continue

            # Construct the full prompt with conversation history
            history = "\n".join(conversations[conversation_id])
            full_prompt = f"{prompt}\n\n[conversation history]\n{history}"

            # Determine working directory for generation outputs
            work_dir = os.getenv('GENERATIONS_DIR', default_output_dir)

            # Build your gemini or AI command here
            gemini_path = os.getenv('GEMINI_PATH', 'gemini')
            command = [
                gemini_path,
                '-y', '-a', '-s',
                '-p', full_prompt,
                '-m', 'gemini-2.5-flash'
            ]

            # Execute the command in the specified directory
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Stream output
            model_response = await stream_command_output(process, websocket)
            await process.wait()

            # Update conversation history only on success
            if process.returncode == 0:
                conversations[conversation_id].extend([
                    f"User: {prompt}",
                    f"Model: {model_response}"
                ])

            # Send final result message
            await websocket.send(json.dumps({'type': 'result', 'returncode': process.returncode}))

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for conversation: {conversation_id}")
    except Exception as e:
        print(f"Error in handler: {e}")
    finally:
        pass

async def main():
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', 'localhost')
    async with websockets.serve(handler, host, port):
        print(f"WebSocket server started at ws://{host}:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())

