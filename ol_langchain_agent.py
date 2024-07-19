from langchain import hub
from langchain.agents import AgentExecutor, create_tool_calling_agent, create_react_agent
from langchain_core.tools import tool
from langchain_community.llms.ollama import Ollama
from langchain_experimental.llms.ollama_functions import OllamaFunctions
from langchain_openai import ChatOpenAI

prompt = hub.pull("hwchase17/react")
prompt.pretty_print()


@tool
def get_current_time(location: str):
    """
    获取天气情况的工具 参数：地点  eg：北京
    :param location 地点 eg:北京
    :return:
    """
    print(f'---{location}---')
    if location == '上海':
        return '28摄氏度'
    elif location == '北京':
        return '12摄氏度'


@tool
def multiply(first_int: int, second_int: int) -> int:
    """
    Multiply two integers together.
    :param first_int: first number
    :param second_int: second number
    :return:
    """
    print(first_int, second_int)
    return first_int * second_int


@tool
def add(first_int: int, second_int: int) -> int:
    "Add two integers."
    return first_int + second_int


@tool
def exponentiate(base: int, exponent: int) -> int:
    "Exponentiate the base to the exponent power."
    return base ** exponent


tools = [multiply, add, exponentiate, get_current_time]
print(multiply.args)

# llm = ChatOpenAI(model="qwen2:7b", openai_api_key='xx', base_url="http://192.168.2.16:8800/v1")
llm = OllamaFunctions(model="qwen2:7b", openai_api_key='xx', base_url="http://192.168.2.16:8800")
# llm = ChatOpenAI(model="gpt-3.5-turbo", openai_api_key='', base_url="http://d.frogchou.com/v1")
# llm = ChatOpenAI(model="moonshot-v1-8k", openai_api_key='', base_url="https://api.moonshot.cn/v1")
agent = create_react_agent(llm, tools, prompt)
# Create an agent executor by passing in the agent and tools
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
agent_executor.invoke(
    {
        "input": "3*5等于多少"
    }
)
