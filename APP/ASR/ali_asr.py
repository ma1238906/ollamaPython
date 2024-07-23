import asyncio
import time

import websockets
import dashscope
from dashscope.audio.asr import (Recognition, RecognitionCallback, RecognitionResult)
from collections import deque
import os

dashscope.api_key = os.getenv('ALIYUN_API_KEY')


class Callback(RecognitionCallback):

    def __init__(self, ws):
        self.ws = ws
        self.mq = asyncio.Queue()
        self.loop = asyncio.get_running_loop()
        self.loop.create_task(self.send_to_client())

    def on_open(self) -> None:
        print('ASR RecognitionCallback open.')

    def on_close(self) -> None:
        print('ASR RecognitionCallback close.')

    def on_error(self, result: RecognitionResult) -> None:
        print('ASR error :',result)

    def on_event(self, result: RecognitionResult) -> None:
        print(result.get_sentence())
        if result.get_sentence()['end_time']:
            self.mq.put_nowait('\n')
        else:
            self.mq.put_nowait(result.get_sentence()['text'])

    async def send_to_client(self):
        try:
            while True:
                message = await self.mq.get()
                if message is None:
                    break
                await self.ws.send_bytes(message.encode('utf-8'))
                self.mq.task_done()
        except Exception as e:
            print(e)
        finally:
            await self.mq.join()

class AliAsrBinary():
    def __init__(self, websocket):
        self.callback = Callback(websocket)
        self.recognition = Recognition(model='paraformer-realtime-v1',
                                       format='pcm',
                                       sample_rate=16000,
                                       callback=self.callback)
        self.recognition.start()
        self.cache = []

    def process_audico(self, audio_binary):
        if not self.recognition._running:
            self.recognition.start()
        self.recognition.send_audio_frame(audio_binary)