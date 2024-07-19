import os

os.environ['OPENAI_API_KEY'] = 'v'
from openai import OpenAI

messages = [{"role": "system", "content": "your a useful AI assistant."}]


def get_answer(query):
    client = OpenAI(
        api_key='sk',
        base_url='http://192.168.2.16:8800/v1/',
    )
    messages.append({"role": "user", "content": query})
    response = client.chat.completions.create(
        model='qwen2:7b',
        messages=messages,
        # functions=functions
        # stream=True
    )
    messages.append({"role": "assistant", "content": response.choices[0].message.content})
    return response


while True:
    query = input('user:')
    if query == '/bye':
        break

    response = get_answer(query)
    # print(response)
    print(f'bot:{response.choices[0].message.content}')
