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


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_info: str


from langchain_core.messages import filter_messages


def filter_state_messages(state: State):
    # This is very simple helper function which only ever uses the last message
    # return messages[-1:]
    # state["messages"] = filter_messages(state["messages"], include_types=['system', 'human', 'ai'])
    state['messages'] = state['messages'][-12:]  # 保留最近的12条聊天记录
    return state


class Assistant:
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

part_2_tools = [
    TavilySearchResults(max_results=1),
    fetch_user_flight_information,
    search_flights,
    lookup_policy,
    update_ticket_to_new_flight,
    cancel_ticket,
    search_car_rentals,
    book_car_rental,
    update_car_rental,
    cancel_car_rental,
    search_hotels,
    book_hotel,
    update_hotel,
    cancel_hotel,
    search_trip_recommendations,
    book_excursion,
    update_excursion,
    cancel_excursion,
]
part_2_assistant_runnable = assistant_prompt | llm.bind_tools(part_2_tools)

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from CustomerSupport.tool_handle_error import _print_event, handle_tool_error, create_tool_node_with_fallback

builder = StateGraph(State)


def user_info(state: State):
    return {"user_info": fetch_user_flight_information.invoke({})}


# NEW: The fetch_user_info node runs first, meaning our assistant can see the user's flight information without
# having to take an action
builder.add_node("fetch_user_info", user_info)
builder.add_edge(START, "fetch_user_info")
builder.add_node("assistant", Assistant(part_2_assistant_runnable))
builder.add_node("tools", create_tool_node_with_fallback(part_2_tools))
builder.add_edge("fetch_user_info", "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
builder.add_edge("tools", "assistant")

memory = MemorySaver()
part_2_graph = builder.compile(
    checkpointer=memory,
    # NEW: The graph will always halt before executing the "tools" node.
    # The user can approve or reject (or even alter the request) before
    # the assistant continues
    interrupt_before=["tools"],
)

import shutil
import uuid

thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        "passenger_id": "3442 587242",
        "thread_id": thread_id,
    }
}

_printed = set()


async def main():
    while True:
        user_input = input('User:')
        if user_input.lower() in ['q', 'quit', 'exit']:
            print('Goodbye')
            break
        else:
            async for event in part_2_graph.astream_events(
                    {"messages": ("user", user_input)}, config, version='v2'
            ):
                if 'event' in event.keys():
                    kind = event["event"]
                    if kind is not None:
                        if kind == "on_chat_model_stream":
                            content = event["data"]["chunk"].content
                            if content:
                                print(content, end='')
                        elif kind == "on_tool_start":
                            print("--")
                            print(
                                f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
                            )
                        elif kind == "on_tool_end":
                            print(f"Done tool: {event['name']}")
                            print(f"Tool output was: {event['data'].get('output')}")
                            print("--")
            snapshot = part_2_graph.get_state(config)
            while snapshot.next:
                user_input = input(
                    "Do you approve of the above actions? Type 'y' to continue;"
                    " otherwise, explain your requested changed.\n\n"
                )
                if user_input.strip() == "y":
                    async for continue_event in part_2_graph.astream_events(
                            None,
                            config,
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
                                    print("--")
                                    print(
                                        f"Starting tool: {continue_event['name']} with inputs: {continue_event['data'].get('input')}"
                                    )
                                elif kind == "on_tool_end":
                                    print(f"Done tool: {continue_event['name']}")
                                    print(f"Tool output was: {continue_event['data'].get('output')}")
                                    print("--")
                else:
                    async for end_event in part_2_graph.astream_events(
                            {
                                "messages": [
                                    ToolMessage(
                                        tool_call_id=snapshot.values["messages"][-1].tool_calls[0]["id"],
                                        content=f"API call denied by user. Reasoning: '{user_input}'. Continue assisting, accounting for the user's input.",
                                    )
                                ]
                            },
                            config,
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
                                    print("--")
                                    print(
                                        f"Starting tool: {end_event['name']} with inputs: {end_event['data'].get('input')}"
                                    )
                                elif kind == "on_tool_end":
                                    print(f"Done tool: {end_event['name']}")
                                    print(f"Tool output was: {end_event['data'].get('output')}")
                                    print("--")
                snapshot = part_2_graph.get_state(config)


if __name__ == "__main__":
    asyncio.run(main())
