# _*_coding:utf-8_*_
# __author: guo
import os

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": os.getenv("PCM_DB_HOST", "127.0.0.1"),
        "NAME": os.getenv("PCM_DB_NAME", "pcm"),
        "PASSWORD": os.getenv("PCM_DB_PASSWORD", ""),
        "PORT": os.getenv("PCM_DB_PORT", "3306"),
        "USER": os.getenv("PCM_DB_USER", "root"),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}
pdf_dir = "/pdf"

REDIS_HOST = os.getenv("PCM_REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("PCM_REDIS_PORT", "6379")

app_id = os.getenv("WECHAT_APP_ID", "")
app_secret = os.getenv("WECHAT_APP_SECRET", "")
wx_env = os.getenv("WECHAT_ENV", "release")

HOST = os.getenv("PCM_PUBLIC_URL", "http://127.0.0.1:5173")
