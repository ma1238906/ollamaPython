import json
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
import uuid
from CustomerSupport_FastAPI_Stream.customerSupport import part_3_graph
from ConnectionManager import manager

app = FastAPI()

thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        "passenger_id": "3442 587242",
        "thread_id": thread_id,
    }
}


@app.websocket("/{path}")
async def websocket_endpoint(websocket: WebSocket, path: str):
    await manager.connect(websocket, path)
    user_token = websocket.query_params['token']
    manager.set_user_token(websocket, user_token)
    stop_event = asyncio.Event()
    task = None
    try:
        while True:
            message = await websocket.receive_text()
            message_json = json.loads(message)
            if "stop" == message_json["type"]:
                stop_event.set()
                if task is not None:
                    task.cancel()
            else:
                stop_event.clear()
                task = asyncio.create_task(process_task(websocket, message_json, stop_event))
    except WebSocketDisconnect:
        if task is not None:
            task.cancel()
            print(f"websocket_id:{id(websocket)} ，客户端关闭socket。")
    except json.JSONDecodeError:
        print(f"接收到非法json，数据为：{message}")
    except Exception as e:
        error_text = str(e)
        print(error_text)


async def process_task(websocket, message_json, stop_event):
    pass


async def generate_chat_responses(message):
    async for event in part_3_graph.astream_events({"messages": ("user", message)}, config=config, version='v2'):
        if 'event' in event.keys():
            kind = event["event"]
            if kind is not None:
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        result_json = {"message": content}
                        yield f'data:{json.dumps(result_json, ensure_ascii=False)}\n\n'
                elif kind == "on_tool_start":
                    print("------")
                    print(f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}")
                elif kind == "on_tool_end":
                    print(f"Done tool: {event['name']}")
                    print(f"Tool output was: {event['data'].get('output')}")
                    print("------")
    snapshot = part_3_graph.get_state(config)
    if snapshot.next:
        tool_name = snapshot.values["messages"][-1].tool_calls[0]["name"]
        result_json = {"tool": tool_name}
        yield f'data:{json.dumps(result_json, ensure_ascii=False)}\n\n'


@app.post('/chat_stream')
async def chat_stream(request: Request):
    try:
        data = await request.json()
        message = data['message']
        if message:
            return StreamingResponse(
                generate_chat_responses(message=message),
                media_type="text/event-stream"
            )
    except Exception as e:
        print(str(e))
        return 403, '服务器内部错误'


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
