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

pdfmetrics.registerFont(TTFont('dlst', os.path.join(BASE_DIR, "conf", "dingliesongtypeface20241217-2.ttf")))


class Command(BaseCommand):

    def add_text(self, title, an, level=0, max_level=0, alignment=TA_LEFT, is_end=False):
        """
        status: 0 大标题  1 题目  2 小分类  3 选项
        """
        kwargs = {
            "name": "CustomStyle",
            "fontName": "dlst",
            "alignment": alignment,
            "fontSize": 12,
            "leading": 14,
            "leftIndent": 0,
        }
        max_font_size = 24
        kwargs["fontSize"] = max_font_size - (4 * level)

        if level == 0:
            kwargs["alignment"] = TA_CENTER
        else:
            kwargs["leftIndent"] = level * 10

        kwargs["leading"] = int(kwargs["fontSize"] * 1.8)

        text = f"{title}  {an}"
        if is_end:
            text = f"{text}<br />"
        return Paragraph(text, ParagraphStyle(**kwargs))

    def handle(self, *args, **options):
        pdf_dir = os.path.join(BASE_DIR, "patient", "pdf")
        os.makedirs(pdf_dir, exist_ok=True)

        p_id = options["p_id"]
        pdf = SimpleDocTemplate(os.path.join(pdf_dir, f"{p_id}.pdf"), pagesize=letter)
        elements = []

        # start_time = time.time()
        max_level = Question.objects.values_list("level", flat=1).order_by("-level").first()
        # print(time.time() - start_time)

        patient = Patient.objects.filter(id=p_id).first()
        patient_info = [
            f"姓名: {patient.name}",
            f"性别: {patient.sex}",
            f"年龄: {patient.age}",
            f"就诊日期: {patient.date.__str__().split(' ', 1)[0]}",
        ]
        elements.append(self.add_text(f"三志堂精神健康测试", "", 0, max_level, alignment=TA_CENTER))
        for i in range(0, len(patient_info), 2):
            cur_patient_info = patient_info[i: i + 2]
            elements.append(self.add_text("   ".join(cur_patient_info), "", 1, max_level, alignment=TA_CENTER))

        ignore_ids = []
        for questions in Answer.gen_questions(patient.id):
            questions = [x for x in questions if x["level"] > 1]
            for n, item in enumerate(questions, 1):
                if item["id"] in ignore_ids:
                    continue

                ignore_ids.append(item["id"])
                title = item["title"]
                if item["title_number"]:
                    title = f'{item["title_number"]}  {title}'

                an = item.get("an", "")

                element = self.add_text(title, an, item["level"], max_level, is_end=len(questions) == n)

                elements.append(element)

        elements.append(self.add_text(patient.result, "", 1, max_level, alignment=TA_CENTER))
        pdf.build(elements)

    def add_arguments(self, parser):
        parser.add_argument("p_id")


if __name__ == '__main__':
    start_time = time.time()
    Command().handle(p_id=79)
    print(time.time() - start_time)
