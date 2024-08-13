from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_core.tools import tool
from langchain_community.vectorstores.chroma import Chroma
from langchain_core.runnables import RunnablePassthrough, Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

embedding_function = OpenAIEmbeddings(model='text-embedding-3-small')

docs = [
    Document(
        page_content="the dog loves to eat pizza", metadata={"source": "animal.txt"}
    ),
    Document(
        page_content="the cat loves to eat lasagna", metadata={"source": "animal.txt"}
    ),
    Document(
        page_content="Alan 住在上海，他有很多钱。", metadata={"source": "animal.txt"}
    ),
]

db = Chroma.from_documents(docs, embedding_function)
retriever = db.as_retriever()


@tool
def multiply(a: int, b: int) -> str:
    """Multiply two integers.

    Args:
        a: First integer
        b: Second integer
    """
    return f"the answer is {a * b * 2}"


@tool
def get_temperature(location: str):
    """
    get the temperature
    Args:
        location:somewhere
    """
    return '25℃'


tools = [multiply, get_temperature]

template = """Answer the question based on the following context:
{context}

Question: {question}
"""
prompt = ChatPromptTemplate.from_template(template)
model = ChatOpenAI(temperature=0, streaming=True, model='gpt-4o-mini')
llm_with_tool = model.bind_tools(tools)

retrieval_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | model
        | StrOutputParser()
)

app = FastAPI()


async def generate_chat_responses(message):
    async for chunk in retrieval_chain.astream(message):
        content = chunk.replace("\n", "<br>")
        yield f"data: {content}\n\n"


async def generate_chat_responses_llm_with_tools(message):
    messages = [SystemMessage('your a useful assistant.'), SystemMessage('I am in Beijing now.'), HumanMessage(message)]
    ai_message = llm_with_tool.invoke(messages)
    messages.append(ai_message)
    for tool_call in ai_message.tool_calls:
        selected_tool = {"get_temperature": get_temperature, "multiply": multiply}[tool_call["name"].lower()]
        tool_output = selected_tool.invoke(tool_call["args"])
        messages.append(ToolMessage(tool_output, tool_call_id=tool_call["id"]))
    print(messages)
    final_result = retrieval_chain.astream(messages)
    async for chunk in final_result:
        yield f'data: {chunk}\n\n'


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/chat_stream/{message}")
async def chat_stream(message: str):
    # return StreamingResponse(generate_chat_responses(message=message), media_type="text/event-stream")
    return StreamingResponse(generate_chat_responses_llm_with_tools(message=message), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)