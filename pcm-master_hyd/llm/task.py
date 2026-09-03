# _*_coding:utf-8_*_
# __author: guo
import hashlib

from pcm.settings import redis_cli

if __name__ == '__main__':
    import os
    import sys

    sys.path.insert(0, "../")

    from django.core.wsgi import get_wsgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pcm.settings")
    application = get_wsgi_application()

import datetime
import uuid

from llm.models import Revise, Record
from llm_utils.client import model_name2client
from patient.models import Patient
from pcm.celery import app
from django.db import transaction

from tools.utils import add_unique_lock


@app.task(bind=True)
@add_unique_lock(args_start_idx=1)
def gen_prescription(self, patient_id, model_name="qwen3-max"):
    client = model_name2client[model_name]
    messages, user, question, doctor = Revise.get_revise_output_msg(patient_id, get_user=True)

    mark = f"gen_prescription-{uuid.uuid4()}-{datetime.datetime.now()}"
    record = Record.gen_llm_out(client, mark, model_name, messages, stream=False)
    # messages.append({'role': 'assistant', 'content': record.output})
    # messages.append({'role': 'user', 'content': content})
    # mark = f"gen_prescription-{uuid.uuid4()}-{datetime.datetime.now()}"
    # prescription_record = Record.gen_llm_out(client, mark, model_name, messages, stream=False)

    with transaction.atomic(using=Revise.objects.db):
        Revise.objects.create(
            r_id=record.id, p_id=patient_id, user=user, question=question, doctor=doctor,
            revise_output=record.output
        )
        Patient.objects.filter(id=patient_id).update(history_show=True)


if __name__ == '__main__':
    gen_prescription(85)
