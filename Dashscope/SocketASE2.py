import asyncio
import websockets
import dashscope
from dashscope.audio.asr import (Recognition, RecognitionCallback, RecognitionResult)
from collections import deque

dashscope.api_key = 'sk-29a8bccb6d6d41c7bdabab97826151fd'


class Callback(RecognitionCallback):

    def __init__(self, ws):
        self.ws = ws
        self.mq = asyncio.Queue()
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self.send_to_client())

    def on_open(self) -> None:
        print('RecognitionCallback open.')

    def on_close(self) -> None:
        print('RecognitionCallback close.')

    def on_event(self, result: RecognitionResult) -> None:
        self.mq.put_nowait(result.get_sentence())

    async def send_to_client(self):
        try:
            while True:
                message = await self.mq.get()
                if message is None:
                    break
                await self.ws.send(str(message))
                self.mq.task_done()
        except Exception as e:
            print(e)
        finally:
            await self.mq.join()


async def handle_client(websocket, path):
    print(f"Client connected: {path}")
    stream = deque()
    callback = Callback(websocket)
    recognition = Recognition(model='paraformer-realtime-v1',
                              format='pcm',
                              sample_rate=8000,
                              callback=callback)

    async def process_message(message):
        if isinstance(message, bytes):
            stream.extend(message)
            read_length = 3200
            if not recognition._running:
                recognition.start()
            while len(stream) >= read_length:
                data_chunk = bytes([stream.popleft() for _ in range(read_length)])
                recognition.send_audio_frame(data_chunk)
        else:
            if message == 'start':
                recognition.start()
            elif message == 'stop':
                recognition.stop()

    try:
        while True:
            message = await websocket.recv()
            await process_message(message)
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        recognition.stop()
        print("Recognition stopped.")


async def main():
    server = await websockets.serve(handle_client, "0.0.0.0", 8765, ssl=None)
    print("WebSocket server started on ws://localhost:8765")
    await server.wait_closed()


# 运行 WebSocket 服务器
asyncio.run(main())
