# _*_coding:utf-8_*_
# __author: guo
import base64
import io

import qrcode


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

img = qrcode.make('http://www.baidu.com')
l = pil_to_base64(img)
img.save('hello.png')
