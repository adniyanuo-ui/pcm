import time
import os

import requests

from pcm.settings import BASE_DIR, app_id, app_secret

if __name__ == '__main__':
    import sys

    sys.path.insert(0, "../")

    from django.core.wsgi import get_wsgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pcm.settings")
    application = get_wsgi_application()

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from patient.models import Patient, Answer
from question.models import Question
from user.models import UserProfile
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from system.models import Scene


class Command(BaseCommand):

    def handle(self, *args, **options):
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        }
        resp = requests.get(url, params=params)
        access_token = resp.json()["access_token"]
        data = {
            "q_type": "school",
            "doctor": "",
        }
        Scene.gen_wx_qr(data, access_token, "高校")
        Scene.gen_wx_qr({"q_type": "company"}, access_token, "企业")
        Scene.gen_wx_qr({"q_type": "gov"}, access_token, "机关单位")


if __name__ == '__main__':
    start_time = time.time()
    Command().handle()
    print(time.time() - start_time)
