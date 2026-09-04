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
    "qwen3.8-max": qwen,
    "qwen3.7-plus": qwen,
    "qwen3.8-flash": qwen,
    "deepseek-v4-pro": deepseek,
    "deepseek-v4-flash": deepseek,
    # 仅为旧记录和旧客户端保留；新请求不再默认使用这些型号。
    "qwen3-max": qwen,
    "qwen3.5-plus": qwen,
    "qwen-turbo": qwen,
    "deepseek-chat": deepseek,
    "deepseek-reasoner": deepseek,
    "doubao-seed-2-0-pro-260215": doubao,
}
model_name2name = {
    "qwen3.8-max": "通义千问 Qwen3.8 Max",
    "qwen3.7-plus": "通义千问 Qwen3.7 Plus",
    "qwen3.8-flash": "通义千问 Qwen3.8 Flash",
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "qwen3-max": "通义千问 Qwen3 Max（旧）",
    "qwen3.5-plus": "通义千问 Qwen3.5 Plus（旧）",
    "qwen-turbo": "通义千问 Turbo（旧）",
    "deepseek-chat": "DeepSeek Chat（旧）",
    "deepseek-reasoner": "DeepSeek Reasoner（旧）",
    "doubao-seed-2-0-pro-260215": "豆包",
}
