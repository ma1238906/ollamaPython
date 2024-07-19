import os

os.environ['OPENAI_API_KEY'] = 'v'
from openai import OpenAI,AsyncOpenAI


class call_openai():
    def __init__(self):
        self.__key = 'OPENAI_API_KEY'
        self.__base_Url = "http://192.168.2.16:8800/v1"
        self.client = AsyncOpenAI(api_key=self.__key, base_url=self.__base_Url)

    # 调用AI接口
    async def chat_completion(self, user_message):
        completion = await self.client.chat.completions.create(
            model="qwen2:7b",
            messages=[
                {"role": "user", "content": user_message},
            ],
            max_tokens=4096,
            stream=True,
            temperature=0.9
        )
        async for chunk in completion:
            if chunk.choices[0].finish_reason != "stop":
                print(chunk.choices[0].delta.content,end='')
            else:
                print('')
                print('-----end----')


llm = call_openai()
# response = llm.chat_completion('壮壮数他家的鸡和兔,有头共16个,有脚共44只,问:壮壮家的鸡和兔共有多少只?')


import asyncio
asyncio.run(llm.chat_completion('蓝牙耳机坏了挂牙科还是耳科?'))
asyncio.run(llm.chat_completion('以秋天为题目写一篇200字文章?'))
# for i in range(0,100):
#     print(response)
