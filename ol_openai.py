from openai import OpenAI


class call_openai():
    def __init__(self):
        self.__key = 'OPENAI_API_KEY'
        self.__base_Url = "http://192.168.2.16:8800/v1"
        self.client = OpenAI(api_key=self.__key, base_url=self.__base_Url)

    # 调用AI接口
    def chat_completion(self, user_message):
        completion = self.client.chat.completions.create(
            model="qwen2:7b",
            messages=[
                {"role": "user", "content": user_message},
            ],
            # max_tokens=4096,
            # stream=True,
            temperature=0.3,  # 生成比较稳定的答复
        )
        return completion.choices[0].message.content


llm = call_openai()
response = llm.chat_completion('壮壮数他家的鸡和兔,有头共16个,有脚共44只,问:壮壮家的鸡和兔共有多少只?')
print(response)

# for i in range(0,100):
#     print(response)
