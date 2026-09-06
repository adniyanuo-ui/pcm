"""Opt-in latency samples using fictional dialogue only; never reads patient records.

Run with the backend venv and explicitly exported development credentials.
"""
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pcm-master_hyd'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pcm.settings')
os.environ.setdefault('PCM_ENV', 'test')
import django
django.setup()
from llm.encounters import generate_json
from llm.voice import validate_sources

dialogue = [
    '虚构软件测试病例。患者说：最近两周食欲差，大便偏稀，每天两次。',
    '医生问：有没有发热？患者说：没有发热，也没有腹痛。',
    '患者说：饭后稍有腹胀，下午容易疲乏，夜里睡眠一般。',
    '医生问：吃过什么药？患者说：药名记不清，剂量也不清楚。',
    '患者说：刚才说两周不准确，是三个星期；没有已知药物过敏。',
    '医生说：舌脉等面诊结果待我稍后补充，不能根据上述对话推测。',
]
for model in sys.argv[1:] or ['deepseek-v4-pro']:
    for repeats in (1, 6):
        segments = [dict(id=f'fictional-recording:{i + 1}', text=text, index=i + 1,
                         start_ms=i * 10000, end_ms=(i + 1) * 10000)
                    for i, text in enumerate(dialogue * repeats)]
        started = time.monotonic()
        try:
            result, actual = generate_json('voice_final', {'segments': segments}, model)
            validate_sources(result, segments)
            print(json.dumps(dict(model=actual, input_chars=sum(len(s['text']) for s in segments),
                seconds=round(time.monotonic() - started, 2), grounded=True, summary=result['summary']), ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps(dict(model=model, seconds=round(time.monotonic() - started, 2),
                                  error_type=type(exc).__name__)), flush=True)
            sys.exit(1)
