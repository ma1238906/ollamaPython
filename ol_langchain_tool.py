from langchain_community.llms.ollama import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool


@tool
def multiply(a: int, b: int) -> int:
    """
    计算两个数字相乘的数学工具
    :param a:
    :param b:
    :return:
    """
    print(a, '*****')
    return a * b


tools = [multiply]

output_parser = StrOutputParser()

llm = Ollama(model="qwen2:7b", base_url="http://192.168.2.16:8800")
llm_with_tool = llm.bind_tools(tools)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are world class technical documentation writer."),
    ("user", "{input}")
])
chain = prompt | llm_with_tool | output_parser

print(chain.invoke({"input": "8*6?"}))
