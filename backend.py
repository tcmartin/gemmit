import asyncio
import json
import os
import websockets
import uuid

# In-memory storage for conversations
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
            
            response = {
                'type': 'stream',
                'stream': stream_name,
                'data': decoded_line
            }
            await websocket.send(json.dumps(response))
        except Exception as e:
            print(f"Error streaming {stream_name}: {e}")
            break

async def stream_command_output(process, websocket):
    """Streams stdout and stderr from a process to the websocket."""
    output_buffer = []
    await asyncio.gather(
        stream_pipe(process.stdout, 'stdout', websocket, output_buffer),
        stream_pipe(process.stderr, 'stderr', websocket, []) # stderr is not part of the response
    )
    return "".join(output_buffer)

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

            gemini_path = 'gemini' #os.path.expanduser('~/.npm-global/bin/gemini')
            command = [
                gemini_path,
                '-y', '-a', '-s',
                '-p', full_prompt,
                '-m' , 'gemini-2.5-flash'
            ]

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            model_response = await stream_command_output(process, websocket)
            
            await process.wait()

            if process.returncode == 0:
                conversations[conversation_id].append(f"User: {prompt}")
                conversations[conversation_id].append(f"Model: {model_response}")

            response = {
                'type': 'result',
                'returncode': process.returncode
            }
            await websocket.send(json.dumps(response))

    except websockets.exceptions.ConnectionClosed:
        print(f"Connection closed for conversation: {conversation_id}")
    except Exception as e:
        print(f"Error in handler: {e}")
    finally:
        # Only delete conversation if it was newly created in this handler instance
        # or if it's truly finished (e.g., explicit end conversation message)
        # For now, we'll keep it for history across multiple prompts in the same conversation
        pass


async def main():
    port = 8000
    async with websockets.serve(handler, "localhost", port):
        print(f"WebSocket server started at ws://localhost:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
