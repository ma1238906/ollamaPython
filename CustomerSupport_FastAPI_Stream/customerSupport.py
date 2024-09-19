import asyncio
from typing import Annotated
import datetime
from dotenv import load_dotenv

load_dotenv('../.env')
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from typing_extensions import TypedDict

from langgraph.graph.message import AnyMessage, add_messages
from langchain_core.messages import HumanMessage


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_info: str


from langchain_core.messages import filter_messages


def filter_state_messages(state: State):
    # 对state中的消息进行裁剪，防止与llm的聊天内容过长，这里只是简单的对长度进行了裁剪。
    # 实际情况可以做的更完善，包括筛选等操作
    # return messages[-1:]
    # state["messages"] = filter_messages(state["messages"], include_types=['system', 'human', 'ai'])
    # state['messages'] = [i for i in state['messages'] if i.content != '']
    # 不能从这里直接过滤message，会造成aimessage与toolmessage不对应的情况，大模型会返回错误。

    # if isinstance(state['messages'][-1], HumanMessage):
    #     state['messages'] = [i for i in state['messages'] if i.content != '']

    state['messages'] = state['messages'][-12:]  # 保留最近的12条聊天记录
    return state


class Assistant():
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(filter_state_messages(state))
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                    not result.content
                    or isinstance(result.content, list)
                    and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful customer support assistant for Swiss Airlines. "
            " Use the provided tools to search for flights, company policies, and other information to assist the user's queries. "
            " When searching, be persistent. Expand your query bounds if the first search returns no results. "
            " If a search comes up empty, expand your search before giving up."
            "\n\nCurrent user:\n\n{user_info}\n"
            "\nCurrent time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.datetime.now())

from CustomerSupport.car_server import *
from CustomerSupport.flight_server import *
from CustomerSupport.hotel_server import *
from CustomerSupport.policy_server import *
from CustomerSupport.trip_recommandations_server import *

part_3_safe_tool = [
    TavilySearchResults(max_result=1),
    fetch_user_flight_information,
    search_flights,
    lookup_policy,
    search_car_rentals,
    search_hotels,
    search_trip_recommendations,
]

part_3_sensitive_tools = [
    update_ticket_to_new_flight,
    cancel_ticket,
    book_car_rental,
    update_car_rental,
    cancel_car_rental,
    book_hotel,
    update_hotel,
    cancel_hotel,
    book_excursion,
    update_excursion,
    cancel_excursion
]

part_3_query_tools = [
    select_by_customer
]

sensitive_tool_names = {t.name for t in part_3_sensitive_tools}
query_tool_names = {t.name for t in part_3_query_tools}

part_3_assistant_runnable = assistant_prompt | llm.bind_tools(
    part_3_safe_tool + part_3_sensitive_tools + part_3_query_tools
)

from typing import Literal
from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from CustomerSupport.tool_handle_error import _print_event, handle_tool_error, create_tool_node_with_fallback

builder = StateGraph(State)


def user_info(state: State):
    return {"user_info": fetch_user_flight_information.invoke({})}


builder.add_node("fetch_user_info", user_info)
builder.add_edge(START, "fetch_user_info")
builder.add_node("assistant", Assistant(part_3_assistant_runnable))
builder.add_node("safe_tools", create_tool_node_with_fallback(part_3_safe_tool))
builder.add_node("sensitive_tools", create_tool_node_with_fallback(part_3_sensitive_tools))
builder.add_node("query_tools", create_tool_node_with_fallback(part_3_query_tools))
builder.add_edge("fetch_user_info", 'assistant')


def route_tools(state: State) -> Literal["safe_tools", "sensitive_tools", "query_tools", "__end__"]:
    """
    通过AI返回的tool的名称判断是哪类tool
    :param state:
    :return:
    """
    next_node = tools_condition(state)
    if next_node == END:
        return END
    ai_message = state["messages"][-1]
    first_tool_call = ai_message.tool_calls[0]
    if first_tool_call["name"] in sensitive_tool_names:
        return "sensitive_tools"
    elif first_tool_call["name"] in query_tool_names:
        return 'query_tools'
    return "safe_tools"


builder.add_conditional_edges("assistant", route_tools)
builder.add_edge("safe_tools", "assistant")
builder.add_edge("sensitive_tools", "assistant")
builder.add_edge("query_tools", 'assistant')

memory = MemorySaver()
part_3_graph = builder.compile(
    checkpointer=memory,
    # 在敏感工具前进行打断
    interrupt_before=["sensitive_tools"],
    interrupt_after=['query_tools']
)

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
            async for event in part_3_graph.astream_events(
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
            snapshot = part_3_graph.get_state(config)
            while snapshot.next:
                if snapshot.next == 'assistant':
                    print('snapshot information:', snapshot.metadata)
                    user_input = input(
                        "Do you approve of the above actions? Type 'y' to continue;"
                        " otherwise, explain your requested changed.\n\n"
                    )
                    if user_input.strip() == "y":
                        async for continue_event in part_3_graph.astream_events(
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
                        async for end_event in part_3_graph.astream_events(
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
                    part_3_graph.update_state(config, {"messages": [new_message]})

                    async for continue_event in part_3_graph.astream_events(
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

                snapshot = part_3_graph.get_state(config)


if __name__ == "__main__":
    asyncio.run(main())
