# region 方式一 通过ollama.chat
import os

os.environ['OLLAMA_HOST'] = 'http://192.168.2.16:8800'
import ollama

print(ollama.list()) #输出可用的模型

response = ollama.chat(
    model='qwen2:7b',
    messages=[
        {
            'role': 'user',
            'content': '解析出收件人地点、公司、收件人和收件人电话\n帮我寄到上海国金中心中心33F, ABC公司，Bikky收就行，电话号码13566778899。我的电话是18988998899，上海杨浦区。',
        },
    ]
)
print(response)
# endregion

# region 方式二 通过Client
from ollama import Client

client = Client(host='http://192.168.2.16:8800')
response = client.chat(
    model='qwen2:7b',
    messages=[
        {
            'role': 'user',
            'content': '解析出收件人地点、公司、收件人和收件人电话\n帮我寄到上海国金中心中心33F, ABC公司，Bikky收就行，电话号码13566778899。我的电话是18988998899，上海杨浦区。',
        },
    ]
)
print(response)
# endregion

def fun_main():
    pass