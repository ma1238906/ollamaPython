from dotenv import load_dotenv

load_dotenv()

from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage
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

model = ChatOpenAI(model='gpt-4o-mini', temperature=0).bind_tools(tools)


# 定义一个方法 检测是否应该继续
def should_continue(state: MessagesState) -> Literal["tools", END]:
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return 'tools'
    return END


# 定义一个方法 调用模型
def call_model(state: MessagesState):
    messages = state['messages']
    print(messages)
    response = model.invoke(messages)
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

# 同步调用graph
final_state = app.invoke(
    {"messages": [HumanMessage(content='what is the weather in shanghai tomorrow.')]},
    config={"configurable": {"thread_id": 1}}
)
print(final_state['messages'][-1].content)
