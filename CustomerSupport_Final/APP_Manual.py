import asyncio
from CustomerSupport_graph import final_graph
from langchain_core.messages import ToolMessage
import uuid

thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        "passenger_id": "3442 587242",
        "thread_id": thread_id,
    }
}
async def main():
    while True:
        user_input = input('User:')
        if user_input.lower() in ['q', 'quit', 'exit']:
            print('Goodbye')
            break
        else:
            async for event in final_graph.astream_events(
                    {"messages": ("user", user_input)}, config=config, version='v2'
            ):
                if 'event' in event.keys():
                    kind = event["event"]
                    if kind is not None:
                        if kind == "on_chat_model_stream":
                            content = event["data"]["chunk"].content
                            if content:
                                print(content, end='')
                        elif kind == "on_tool_start":
                            print("------")
                            print(
                                f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
                            )
                        elif kind == "on_tool_end":
                            print(f"Done tool: {event['name']}")
                            print(f"Tool output was: {event['data'].get('output')}")
                            print("------")
            print('\n')
            snapshot = final_graph.get_state(config)
            while snapshot.next:
                if snapshot.next == 'assistant':
                    print('snapshot information:', snapshot.metadata)
                    user_input = input(
                        "Do you approve of the above actions? Type 'y' to continue;"
                        " otherwise, explain your requested changed.\n\n"
                    )
                    if user_input.strip() == "y":
                        async for continue_event in final_graph.astream_events(
                                None,
                                config=config,
                                version='v2'
                        ):
                            if 'event' in continue_event.keys():
                                kind = continue_event["event"]
                                if kind is not None:
                                    if kind == "on_chat_model_stream":
                                        content = continue_event["data"]["chunk"].content
                                        if content:
                                            print(content, end='')
                                    elif kind == "on_tool_start":
                                        print("------")
                                        print(
                                            f"Starting tool: {continue_event['name']} with inputs: {continue_event['data'].get('input')}"
                                        )
                                    elif kind == "on_tool_end":
                                        print(f"Done tool: {continue_event['name']}")
                                        print(f"Tool output was: {continue_event['data'].get('output')}")
                                        print("------")
                        print('\n')
                    else:
                        async for end_event in final_graph.astream_events(
                                {
                                    "messages": [
                                        ToolMessage(
                                            tool_call_id=snapshot.values["messages"][-1].tool_calls[0]["id"],
                                            content=f"API call denied by user. Reasoning: '{user_input}'. Continue assisting, accounting for the user's input.",
                                        )
                                    ]
                                },
                                config=config,
                                version='v2'
                        ):
                            if 'event' in end_event.keys():
                                kind = end_event["event"]
                                if kind is not None:
                                    if kind == "on_chat_model_stream":
                                        content = end_event["data"]["chunk"].content
                                        if content:
                                            print(content, end="")
                                    elif kind == "on_tool_start":
                                        print("------")
                                        print(
                                            f"Starting tool: {end_event['name']} with inputs: {end_event['data'].get('input')}"
                                        )
                                    elif kind == "on_tool_end":
                                        print(f"Done tool: {end_event['name']}")
                                        print(f"Tool output was: {end_event['data'].get('output')}")
                                        print("------")
                        print('\n')
                else:
                    user_input = input('请用户手动输入内容：')
                    # 使用用户输入的内容更新最后一条消息
                    existing_message = snapshot.values["messages"][-1]
                    new_message = ToolMessage(
                        content=user_input,
                        id=existing_message.id,
                        tool_call_id=existing_message.tool_call_id
                    )
                    final_graph.update_state(config, {"messages": [new_message]})

                    async for continue_event in final_graph.astream_events(
                            None,
                            config=config,
                            version='v2'
                    ):
                        if 'event' in continue_event.keys():
                            kind = continue_event["event"]
                            if kind is not None:
                                if kind == "on_chat_model_stream":
                                    content = continue_event["data"]["chunk"].content
                                    if content:
                                        print(content, end='')
                                elif kind == "on_tool_start":
                                    print("------")
                                    print(
                                        f"Starting tool: {continue_event['name']} with inputs: {continue_event['data'].get('input')}"
                                    )
                                elif kind == "on_tool_end":
                                    print(f"Done tool: {continue_event['name']}")
                                    print(f"Tool output was: {continue_event['data'].get('output')}")
                                    print("------")
                    print('\n')

                snapshot = final_graph.get_state(config)


if __name__ == "__main__":
    asyncio.run(main())