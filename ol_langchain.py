from langchain_community.llms.ollama import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

output_parser = StrOutputParser()

llm = Ollama(model="qwen2:7b",base_url="http://192.168.2.16:8800")
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are world class technical documentation writer."),
    ("user", "{input}")
])
chain = prompt | llm | output_parser

print(chain.invoke({"input": "北京历史名迹?"}))
