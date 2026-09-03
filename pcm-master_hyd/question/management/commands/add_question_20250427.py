#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import re

from tqdm import tqdm

from pcm.settings import BASE_DIR

if __name__ == '__main__':
    import os
    import sys

    sys.path.insert(0, "../")

    from django.core.wsgi import get_wsgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pcm.settings")
    application = get_wsgi_application()

import cn2an
import datetime
import os.path

from django.core.management.base import BaseCommand
from django.db.models import Q
from question.models import Question


class Command(BaseCommand):

    def handle(self, *args, **options):
        Question.add_q_20250427()


if __name__ == '__main__':
    Command().handle()
