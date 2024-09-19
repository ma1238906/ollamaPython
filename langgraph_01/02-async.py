import asyncio

from dotenv import load_dotenv

load_dotenv()

from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode


# 定义一个工具
@tool
def search(query: str):
    """
    Get weather.
    Please note that this method can only get today's weather.
    :param query:location
    :return:
    """
    if 'sf' in query.lower() or 'san francisco' in query.lower():
        return ['It`s 60 degrees and foggy.']
    return ['It`s 90 degrees and sunny.']


tools = [search]
# 定义一个工具节点
tool_node = ToolNode(tools)

model = ChatOpenAI(model='moonshot-v1-8k', temperature=0).bind_tools(tools)


# 定义一个方法 检测是否应该继续
def should_continue(state: MessagesState) -> Literal["tools", END]:
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return 'tools'
    return END


# 定义一个方法 调用模型
async def call_model(state: MessagesState, config: RunnableConfig):
    messages = state['messages']
    print(messages)
    response = await model.ainvoke(messages, config)
    return {"messages": [response]}


# 声明一个graph
workflow = StateGraph(MessagesState)

# 定义graph的节点
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# 设置graph的入口点
workflow.set_entry_point("agent")

# 为graph添加edge
workflow.add_conditional_edges("agent", should_continue)

# 为tool节点添加 返回到agent节点的边
workflow.add_edge("tools", "agent")

# 为graph执行添加记录
check_pointer = MemorySaver()

# 编译graph
app = workflow.compile(checkpointer=check_pointer)


async def main():
    inputs = [HumanMessage(content="写500字左右的故事")]
    async for event in app.astream_events({"messages": inputs}, config={"configurable": {"thread_id": 1}},
                                          version='v2'):
        if 'event' in event.keys():
            kind = event["event"]
            if kind is not None:
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        print(content, end="|")
                elif kind == "on_tool_start":
                    print("--")
                    print(
                        f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
                    )
                elif kind == "on_tool_end":
                    print(f"Done tool: {event['name']}")
                    print(f"Tool output was: {event['data'].get('output')}")
                    print("--")


if __name__ == "__main__":
    asyncio.run(main())
