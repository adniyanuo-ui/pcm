# _*_coding:utf-8_*_
# __author: guo
import os

from openai import OpenAI

OPEN_AI_LLM_CONF = {
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key": os.getenv("QWEN_API_KEY", "")
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "api_key": os.getenv("DEEPSEEK_API_KEY", "")
    },
    "doubao": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key": os.getenv("DOUBAO_API_KEY", ""),
    }
}
qwen = OpenAI(**OPEN_AI_LLM_CONF["qwen"])
deepseek = OpenAI(**OPEN_AI_LLM_CONF["deepseek"])
doubao = OpenAI(**OPEN_AI_LLM_CONF["doubao"])
model_name2client = {
    "qwen3-max": qwen,
    "qwen3.5-plus": qwen,
    "qwen-turbo": qwen,
    "deepseek-chat": deepseek,
    "deepseek-reasoner": deepseek,
    "doubao-seed-2-0-pro-260215": doubao,
}
model_name2name = {
    "qwen3-max": "通义千问-max",
    "qwen3.5-plus": "通义千问-plus",
    "qwen-turbo": "通义千问-turbo",
    "deepseek-chat": "deepseek V3",
    "deepseek-reasoner": "deepseek R1",
    "doubao-seed-2-0-pro-260215": "豆包",
}
