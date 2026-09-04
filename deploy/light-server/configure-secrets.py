#!/usr/bin/env python3
import getpass
import os
from pathlib import Path
import sys
import tempfile


def main() -> None:
    env_path = Path(sys.argv[1])
    lines = env_path.read_text(encoding="utf-8").splitlines()
    current = {}
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip()] = value.strip().strip("'\"")

    prompts = (
        ("DEEPSEEK_API_KEY", "DeepSeek API Key（默认使用 V4 Pro）"),
        ("QWEN_API_KEY", "通义千问 API Key（备用使用 Qwen3.7 Plus，可留空）"),
        ("ALIYUN_ACCESS_KEY_ID", "阿里云 AccessKey ID"),
        ("ALIYUN_ACCESS_KEY_SECRET", "阿里云 AccessKey Secret"),
        ("ALIYUN_NLS_APPKEY", "智能语音交互项目 AppKey"),
    )

    updates = {}
    print("输入内容不会显示；直接回车会保留原值。")
    for key, label in prompts:
        state = "已配置" if current.get(key) else "未配置"
        value = getpass.getpass(f"{label}（{state}）：").strip()
        if value:
            if any(char in value for char in ("\n", "\r", "\0", "'")):
                raise SystemExit(f"{label} 含不支持的字符")
            updates[key] = value

    model_choices = {
        "1": "deepseek-v4-pro",
        "2": "deepseek-v4-flash",
        "3": "qwen3.7-plus",
    }
    current_model = current.get("PCM_DEFAULT_LLM_MODEL") or "deepseek-v4-pro"
    print(f"当前默认模型：{current_model}")
    print("1=DeepSeek V4 Pro（推荐）  2=DeepSeek V4 Flash（低成本）  3=Qwen3.7 Plus（备用）")
    try:
        choice = input("切换默认模型〔直接回车保留〕：").strip()
    except EOFError:
        # 非交互执行时安全地保留当前模型。
        choice = ""
    if choice:
        if choice not in model_choices:
            raise SystemExit("模型选择无效，请输入 1、2、3 或直接回车")
        updates["PCM_DEFAULT_LLM_MODEL"] = model_choices[choice]

    if not updates:
        print("没有修改配置。")
        return

    seen = set()
    output = []
    for line in lines:
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in updates:
                output.append(f"{key}='{updates[key]}'")
                seen.add(key)
                continue
        output.append(line)
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}='{value}'")

    fd, temp_name = tempfile.mkstemp(prefix=".env.", dir=env_path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(output) + "\n")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, env_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print("密钥已安全写入，配置文件权限为 600。")


if __name__ == "__main__":
    main()
