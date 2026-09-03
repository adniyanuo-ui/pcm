import os
from pathlib import Path


DEV_BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("PCM_SQLITE_PATH", DEV_BASE_DIR / "var" / "db.sqlite3"),
    }
}

pdf_dir = os.getenv("PCM_PDF_DIR", "")
app_id = os.getenv("WECHAT_APP_ID", "")
app_secret = os.getenv("WECHAT_APP_SECRET", "")
wx_env = os.getenv("WECHAT_ENV", "")
