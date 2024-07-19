import asyncio
import datetime
import threading

import websockets
import dashscope
import random
from dashscope.audio.asr import (Recognition, RecognitionCallback, RecognitionResult)

dashscope.api_key = 'sk-29a8bccb6d6d41c7bdabab97826151fd'


class Callback(RecognitionCallback):

    def __init__(self, ws):
        self.ws = ws
        self.mq = asyncio.Queue()  # 使用asyncio的队列以确保线程安全
        self.loop = asyncio.get_running_loop()  # 获取当前运行的事件循环

        # 使用线程安全的队列和事件循环安排协程任务
        self.loop.create_task(self.send_to_client())

    def on_open(self) -> None:
        print('RecognitionCallback open.')

    def on_close(self) -> None:
        print('RecognitionCallback close.')

    def on_event(self, result: RecognitionResult) -> None:
        # print('识别结果: ', result.get_sentence())
        # 将消息安全地放入队列
        self.mq.put_nowait(result.get_sentence())
        # print('mq队列数据', self.mq.qsize())

    async def send_to_client(self):
        try:
            while True:
                # Check if there are messages in the queue
                while self.mq.qsize() > 0:
                    message = await self.mq.get()
                    if message is None:
                        break
                    # print('Sending to client:', message)
                    await self.ws.send(str(message))
                    self.mq.task_done()
                await asyncio.sleep(0.1)  # Wait briefly before checking again
        except Exception as e:
            print(e)
        finally:
            await self.mq.join()


async def handle_client(websocket, path):
    print(f"Client connected: {path}")
    stream = bytearray()
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
                data_chunk = stream[:read_length]
                recognition.send_audio_frame(data_chunk)
                del stream[:read_length]
        else:
            if message == 'start':
                recognition.start()
            elif message == 'stop':
                recognition.stop()

    try:
        while True:
            message = await websocket.recv()
            asyncio.create_task(process_message(message))
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
