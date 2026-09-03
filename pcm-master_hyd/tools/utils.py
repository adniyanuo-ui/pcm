# _*_coding:utf-8_*_
# __author: guo
import base64
import functools
import hashlib
import io
import os
import time

from pcm.settings import redis_cli


def try_for(num=3, sleep_time=20):
    def middle(func):
        def inner(*args, **kwargs):
            for i in range(num):
                try:
                    ret = func(*args, **kwargs)
                    return ret
                except Exception as e:
                    if i == (num - 1):
                        raise e
                    print(e)
                    time.sleep(sleep_time)

        return inner

    return middle


def add_unique_lock(ex=1 * 60 * 60, args_start_idx=0):
    def middle(func):
        # fun.__name__, fun.__module__
        @functools.wraps(func)
        def inner(*args, **kwargs):
            key_args = args[args_start_idx:]
            x = hashlib.md5(f"{key_args}-{kwargs}".encode()).hexdigest()
            redis_key = f"{func}:{x}"
            f = int(redis_cli.get(redis_key) or 0)
            if f:
                return "正在运行"

            redis_cli.set(redis_key, 1, ex=ex)
            try:
                return func(*args, **kwargs)
            finally:
                redis_cli.set(redis_key, 0)

        return inner

    return middle


def pil_to_base64(img, format='PNG'):
    """
    将 PIL Image 对象转换为 Base64 字符串

    Args:
        img: PIL Image 对象
        format: 图像格式 ('PNG', 'JPEG', 'WEBP' 等)

    Returns:
        Base64 编码的字符串（包含 data URI scheme）
    """
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # 返回带 data URI scheme 的字符串（可直接用于 HTML img src）
    return f"data:image/{format.lower()};base64,{img_str}"
