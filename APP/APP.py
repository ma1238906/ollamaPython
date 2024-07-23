from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Response,
    Query,
    UploadFile,
    File,
)
import asyncio, json
from utils.log_utils import Logger
from settings import *
from TTS.ali_tts import tts as ali_tts
from ASR.ali_asr import AliAsrBinary
from typing import List

# 设置日志记录器
logger = Logger("APP", log_file='Logs/log.txt').get_logger()

# 初始化FastAPI应用
app = FastAPI()


@app.post('/tts')
async def tts_post(request: Request):
    """
    {"type","tts","content","xxxxx"}
    :param request:
    :return:
    """
    try:
        req_json = await request.json()
        text = req_json['content']
        audio = ali_tts(text)
        if audio:
            return Response(audio, media_type='audio/wav')
        else:
            return {"error": "tts error"}
    except Exception as e:
        return {"error": str(e)}


@app.get('/tts')
async def tts_get(content: str = Query(default=" ", description="TTS的文字")):
    """
    
    :param content:
    :return:
    """
    print(content)
    audio = ali_tts(content)
    if audio:
        return Response(audio, media_type='audio/wav')
    else:
        return {"error": "tts error"}


# websocket的连接管理器
class ConnectionManager:
    def __init__(self):
        self.asr_instances = {}
        self.active_connections: List[WebSocket] = []

    # 接受WebSocket连接并将其添加到活动连接列表
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    # 断开WebSocket连接并将其从活动连接列表中移除
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    # 发送单独消息给指定的WebSocket连接
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    # 向所有活动连接广播消息
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    def get_asr_instance(self, websocket: WebSocket):
        if websocket not in self.asr_instances:
            self.asr_instances[websocket] = AliAsrBinary(websocket)
        return self.asr_instances[websocket]


manager = ConnectionManager()


@app.websocket("/{path}")
async def websocket_endpoint(websocket: WebSocket, path: str):
    await manager.connect(websocket)
    stop_event = asyncio.Event()
    try:
        if path == 'asr':
            asr_instance = manager.get_asr_instance(websocket)
            async for message in websocket.iter_bytes():
                await process_asr(message,asr_instance)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        del manager.asr_instances[websocket]
        logger.info("Connection closed")
    except json.JSONDecodeError:
        logger.error(f"接收到非法json，数据为：{message}")


async def process_asr(binary_message,asr):
    asr.process_audico(binary_message)


if __name__ == "__main__":
    import uvicorn

    print("""  

    """)
    logger.info("server start")
    uvicorn.run(app, host=IP_ADDR, port=int(IP_PORT), log_level="warning")
