import threading
import queue
import websockets
import pyaudio
import asyncio

# 设置音频参数
CHUNK = 3200  # 每次读取的音频数据长度
FORMAT = pyaudio.paInt16  # 数据流格式
CHANNELS = 1  # 声道数
RATE = 16000  # 音频采样率

# 创建一个线程安全的队列
audio_queue = queue.Queue()

def capture_audio():
    p = pyaudio.PyAudio()  # 初始化PyAudio对象

    # 打开音频流
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True)

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_queue.put(data)

    finally:
        # 停止并关闭音频流
        stream.stop_stream()
        stream.close()

        # 终止PyAudio
        p.terminate()

async def send_audio(uri):
    async with websockets.connect(uri) as websocket:
        print(f"Connected to {uri}")

        # 接收消息的任务
        async def receive_messages():
            while True:
                message = await websocket.recv()
                print(f"Received message from server: {message}")

        # 发送音频的任务
        async def send_audio_data():
            while True:
                data = await asyncio.to_thread(audio_queue.get)
                await websocket.send(data)

        # 创建任务来发送音频数据和接收消息
        send_task = asyncio.create_task(send_audio_data())
        receive_task = asyncio.create_task(receive_messages())

        # 等待任务完成
        done, pending = await asyncio.wait(
            [send_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # 取消未完成的任务
        for task in pending:
            task.cancel()

        # 获取已完成的任务的结果（如果有的话）
        for task in done:
            try:
                task.result()  # 这将抛出异常，如果任务因为异常而取消
            except Exception as e:
                print(f"Task error: {e}")

def start_capture():
    # 启动音频捕获线程
    capture_thread = threading.Thread(target=capture_audio)
    capture_thread.daemon = True
    capture_thread.start()

# WebSocket服务器的地址和端口
uri = "ws://localhost:8765"
# uri = 'wss://voice.lkz.fit/recognition'

# 启动音频捕获线程
start_capture()

# 运行发送音频的异步任务
asyncio.run(send_audio(uri))
