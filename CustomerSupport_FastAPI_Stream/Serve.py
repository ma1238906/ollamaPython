from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
import uuid
from CustomerSupport_FastAPI_Stream.customerSupport import part_3_graph

app = FastAPI()

thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        "passenger_id": "3442 587242",
        "thread_id": thread_id,
    }
}


async def generate_chat_responses(message):
    async for event in part_3_graph.astream_events({"messages": ("user", message)}, config=config, version='v2'):
        if 'event' in event.keys():
            kind = event["event"]
            if kind is not None:
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f'data:{content}\n\n'
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
        yield f'data:{tool_name}\n\n'


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
