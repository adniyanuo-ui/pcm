import re
import time
import os

from pcm.settings import BASE_DIR

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
from patient.management.commands.to_pdf import Command as ToPdf


class Command(BaseCommand):

    def handle(self, *args, **options):
        for obj in Patient.objects.exclude(result=""):
            score, anxiety_level, yiyu_level = re.findall(r"\d+", obj.result)
            Patient.objects.filter(id=obj.id).update(score=score, anxiety_level=anxiety_level, yiyu_level=yiyu_level)
            ToPdf().handle(p_id=obj.id)


if __name__ == '__main__':
    start_time = time.time()
    Command().handle(p_id=27)
    print(time.time() - start_time)
