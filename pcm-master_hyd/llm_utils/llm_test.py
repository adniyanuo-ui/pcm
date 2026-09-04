# _*_coding:utf-8_*_
# __author: guo
import json
import time

from openai import OpenAI

from llm_utils.client import OPEN_AI_LLM_CONF, model_name2client

model_name = "deepseek-v4-pro"
client = model_name2client[model_name]
completion = client.chat.completions.create(
    model=model_name,
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': '你是谁？'}
    ],
    stream=True,
    stream_options={"include_usage": True}
)
for i in completion:
    a = json.loads(i.model_dump_json())
    print()
