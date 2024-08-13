import os
from dotenv import load_dotenv

load_dotenv()
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

llm = ChatOpenAI(
    temperature=0.0,
    model_name="gpt-4o-mini",
    streaming=True,  # ! important
    callbacks=[StreamingStdOutCallbackHandler()]  # ! important
)

from langchain.schema import HumanMessage

# create messages to be passed to chat LLM
messages = [HumanMessage(content="tell me a short story")]

# re = llm(messages)
# print(re)
######################

from langchain.memory import ConversationBufferWindowMemory
from langchain.agents import AgentType, initialize_agent
from langchain_community.agent_toolkits.load_tools import load_tools

# initialize conversational memory
memory = ConversationBufferWindowMemory(
    memory_key="chat_history",
    k=5,
    return_messages=True,
    output_key="output"
)


@tool
def show_map(location: str):
    """显示对应地点的地图,可选的地点包括（点A、点B、点C），其他地点不可以显示.

        Args:
            location: 地点名称
        """
    print(f"location:{location}")
    return '直行200米就到了'


# create a single tool to see how it impacts streaming
# tools = load_tools(["llm-math"], llm=llm)
tools = [show_map]

# initialize the agent
agent = initialize_agent(
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    tools=tools,
    llm=llm,
    memory=memory,
    verbose=False,
    max_iterations=3,
    early_stopping_method="generate",
    return_intermediate_steps=False
)
import sys


class CallbackHandler(StreamingStdOutCallbackHandler):
    def __init__(self):
        self.content: str = ""
        self.final_answer: bool = False

    def on_llm_new_token(self, token: str, **kwargs: any) -> None:
        self.content += token
        if "Final Answer" in self.content:
            # now we're in the final answer section, but don't print yet
            self.final_answer = True
            self.content = ""
        if self.final_answer:
            if '"action_input": "' in self.content:
                if token not in ["}"]:
                    sys.stdout.write(token)  # equal to `print(token, end="")`
                    sys.stdout.flush()


agent.agent.llm_chain.llm.callbacks = [CallbackHandler()]

prompt = "到点A怎么走"
agent(prompt)
# print(agent(prompt))
