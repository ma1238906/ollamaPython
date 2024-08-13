import os
import asyncio
from typing import Any
from dotenv import load_dotenv

load_dotenv()

import uvicorn
from fastapi import FastAPI, Body
from fastapi.responses import StreamingResponse
from queue import Queue
from pydantic import BaseModel

from langchain.agents import AgentType, initialize_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler
from langchain.schema import LLMResult
from langchain_core.tools import tool

app = FastAPI()

# 初始化agent
llm = ChatOpenAI(
    temperature=0.0,
    model_name="gpt-4o-mini",
    streaming=True,  # ! important
    callbacks=[]  # ! important 后面会加入callback处理
)

memory = ConversationBufferWindowMemory(
    memory_key='chat_history',
    k=5,
    return_messages=True,
    output_key="output"
)


@tool
def say_something(text_to_say: str):
    """
    使用播放器播放输入的文字
    Args:
        text_to_say: 要播放的内容.
    """
    print(text_to_say,'----------')
    return 'task complete!'


agent = initialize_agent(
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    tools=[say_something],
    llm=llm,
    verbose=True,
    max_iterations=3,
    early_stopping_method="generate",
    memory=memory,
    return_intermediate_steps=False
)


class AsyncCallbackHandler(AsyncIteratorCallbackHandler):
    content: str = ""
    final_answer: bool = False

    def __init__(self) -> None:
        super().__init__()

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        self.content += token
        # if we passed the final answer, we put tokens in queue
        if self.final_answer:
            if '"action_input": "' in self.content:
                if token not in ['"', "}"]:
                    self.queue.put_nowait(token)
        elif "Final Answer" in self.content:
            self.final_answer = True
            self.content = ""

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        if self.final_answer:
            self.content = ""
            self.final_answer = False
            self.done.set()
        else:
            self.content = ""


async def run_call(query: str, stream_it: AsyncCallbackHandler):
    agent.agent.llm_chain.llm.callbacks = [stream_it]
    await agent.acall(inputs={'input': query})


class Query(BaseModel):
    text: str


async def create_gen(query: str, stream_it: AsyncCallbackHandler):
    task = asyncio.create_task(run_call(query, stream_it))
    async for token in stream_it.aiter():
        yield token
    await task


@app.post("/chat")
async def chat(
        query: Query = Body(...),
):
    stream_it = AsyncCallbackHandler()
    gen = create_gen(query.text, stream_it)
    return StreamingResponse(gen, media_type="text/event-stream")


async def chat_l(text):
    stream_it = AsyncCallbackHandler()
    gen = create_gen(text, stream_it)
    return StreamingResponse(gen, media_type='text/event-stream')


@app.get("/health")
async def health():
    """Check the api is running"""
    return {"status": "🤙"}


if __name__ == "__main__":
    uvicorn.run(app=app, host="0.0.0.0", port=8000)
    # asyncio.run(chat_l('hello'))
