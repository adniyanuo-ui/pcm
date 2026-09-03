import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


PILOT_BASE_DIR = Path(__file__).resolve().parent.parent
PILOT_DOMAIN = os.getenv("PCM_DOMAIN", "").strip()
if not PILOT_DOMAIN:
    raise ImproperlyConfigured("PCM_ENV=pilot 时必须配置 PCM_DOMAIN")
if not os.getenv("DJANGO_SECRET_KEY"):
    raise ImproperlyConfigured("PCM_ENV=pilot 时必须配置 DJANGO_SECRET_KEY")

DEBUG = False
ALLOWED_HOSTS = [PILOT_DOMAIN, "127.0.0.1", "localhost", "api"]
CSRF_TRUSTED_ORIGINS = [f"https://{PILOT_DOMAIN}"]
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOWED_ORIGINS = [f"https://{PILOT_DOMAIN}"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("PCM_SQLITE_PATH", PILOT_BASE_DIR / "var" / "db.sqlite3"),
        "OPTIONS": {"timeout": 20},
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

pdf_dir = os.getenv("PCM_PDF_DIR", "")
app_id = os.getenv("WECHAT_APP_ID", "")
app_secret = os.getenv("WECHAT_APP_SECRET", "")
wx_env = os.getenv("WECHAT_ENV", "")
