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
    """
    去掉无关信息、题目之间添加空格

    """
    # 八、九
    text = """"""

    def add_question(self, data, parent_obj=None):
        for item in data:
            children = item.pop("children", [])
            obj = Question.objects.create(**item, parent=parent_obj)
            self.add_question(children, obj)

    def get_cur_text(self, idx, li, this_obj, text) -> str:
        if idx + 1 == len(li):
            cur_text = text[this_obj.end():]
        else:
            next_obj = li[idx + 1]
            cur_text = text[this_obj.end(): next_obj.start()]

        return cur_text

    def get_level0(self):
        num_re = f"[一二三四五六七八九十]+、"
        li = list(re.finditer(rf"({num_re}.*?)[ \n]", self.text, re.S))
        for idx, this_obj in enumerate(li):
            title = this_obj.group(0).strip()
            cur_text = self.get_cur_text(idx, li, this_obj, self.text)
            num = re.search(num_re, title).group(0)
            title = title.replace(num, "").strip()
            num = num.replace("、", "")
            yield num, title, cur_text

    def get_jl_yu(self, text, is_op=False):
        new_text = text
        yu = []
        jl = []
        jl_yu_li = re.findall(r"[(（]([\d焦虑抑郁症定性题级之一、，, ]*?)[)）]", text)
        if jl_yu_li:
            for jl_yu_text in jl_yu_li:
                jl_yu_text = jl_yu_text.strip()
                if jl_yu_text:
                    for txt in re.split(r"[ ，,、]", jl_yu_text):
                        txt = txt.strip()
                        if txt:
                            _type = "之一" if "之一" in txt else "定性"
                            level_li = re.findall(r"(\d+)", txt)
                            if "抑郁" in txt:
                                yu.append({"type": _type, "level": int(level_li[0]) if level_li else 0})
                            elif "焦虑" in txt:
                                jl.append({"type": _type, "level": int(level_li[0]) if level_li else 0})
                new_text = new_text.replace(jl_yu_text, "")

        if is_op:
            return new_text, jl, yu
        else:
            return new_text, jl[0] if jl else None, yu[0] if yu else None

    def get_level1(self, text):
        li = list(re.finditer(r"\d+\.\d+(\.?\d+)?", text, re.S))
        li = [x for x in li if not re.findall(r"\d+\.\d+\.\d+", x.group(0).strip())]
        for idx, this_obj in enumerate(li):
            num = this_obj.group(0).strip()
            cur_text = self.get_cur_text(idx, li, this_obj, text)
            title = cur_text.split("\n", 1)[0].strip()
            cur_text = cur_text.replace(title, "").strip()

            title, jl, yu = self.get_jl_yu(title)

            yield num, title, cur_text, jl, yu

    def get_level2(self, text):
        li = list(re.finditer(r"\d+\.\d+\.\d+(\.?\d+)?", text, re.S))
        li = [x for x in li if not re.findall(r"\d+\.\d+\.\d+\.\d+", x.group(0).strip())]
        for idx, this_obj in enumerate(li):
            num = this_obj.group(0).strip()
            cur_text = self.get_cur_text(idx, li, this_obj, text)
            title = cur_text.split("\n", 1)[0].strip()
            cur_text = cur_text.replace(title, "").strip()

            title, jl, yu = self.get_jl_yu(title)
            title = re.sub(r"[(（] *?[)）]", "()", title)
            is_select = "()" in title
            title = title.replace("()", "").strip()

            yield num, title, cur_text, is_select, jl, yu

    def get_level3(self, text):
        li = list(re.finditer(r"\d+\.\d+\.\d+\.\d+(\.?\d+)?", text, re.S))
        li = [x for x in li if not re.findall(r"\d+\.\d+\.\d+\.\d+\.\d+", x.group(0).strip())]
        for idx, this_obj in enumerate(li):
            num = this_obj.group(0).strip()
            cur_text = self.get_cur_text(idx, li, this_obj, text)
            title = cur_text.split("\n", 1)[0].strip()
            cur_text = cur_text.replace(title, "").strip()

            title, jl, yu = self.get_jl_yu(title)
            title = re.sub(r"[(（] *?[)）]", "()", title)
            is_select = "()" in title
            title = title.replace("()", "").strip()

            yield num, title, cur_text, is_select, jl, yu

    def get_op(self, text):
        text, jl_li, yu_li = self.get_jl_yu(text, is_op=True)

        new_text = re.sub(r" *[(（] *?[)）]", "()", text)
        new_text = re.sub(r"[,，]", ",", new_text)
        new_text = re.sub(r"[、]", "、", new_text)
        li = re.findall("([a-zA-Z0-9\u4e00-\u9fff/(,、]+)?", new_text)

        n = 0
        for op in li:
            if op:
                jl = jl_li[n] if n < len(jl_li) else None
                yu = yu_li[n] if n < len(yu_li) else None
                n += 1
                yield op.replace("(", ""), "(" in op, jl, yu

    def parse_question(self):
        result = []
        for order, (num, title, text) in enumerate(self.get_level0(), 1):
            print(f"{num}、{title}")
            tmp = {
                "title": title,
                "title_number": num,
                "mode": -1,
                "order": order,
                "children": []
            }
            result.append(tmp)

            for order1, (num1, title1, text1, jl, yu) in enumerate(self.get_level1(text), 1):
                # title1占一个页面
                print(f"=========================={num1}、{title1}, {jl}, {yu}")
                tmp1 = {
                    "title": title1,
                    "title_number": num1,
                    "mode": -1,
                    "order": order1,
                    "jl": jl or {},
                    "yu": yu or {},
                    "children": []
                }
                tmp["children"].append(tmp1)
                for order2, (num2, title2, text2, is_select2, jl, yu) in enumerate(self.get_level2(text1), 1):
                    print(f"{is_select2}, {num2}、{title2}, {jl}, {yu}")
                    tmp2 = {
                        "title": title2,
                        "title_number": num2,
                        "mode": 3 if is_select2 else -1,
                        "order": order2,
                        "jl": jl or {},
                        "yu": yu or {},
                        "children": []
                    }
                    tmp1["children"].append(tmp2)
                    level3_li = list(self.get_level3(text2))
                    if not level3_li:
                        if text2:
                            for op_order2, (op2, op_is_select2, jl, yu) in enumerate(self.get_op(text2), 1):
                                print("op2", op_is_select2, op2, jl, yu)
                                op_tmp2 = {
                                    "title": op2,
                                    "title_number": "",
                                    "mode": 3 if op_is_select2 else -1,
                                    "order": op_order2,
                                    "jl": jl or {},
                                    "yu": yu or {},
                                    "children": []
                                }
                                tmp2["children"].append(op_tmp2)
                    else:
                        for order3, (num3, title3, text3, is_select3, jl, yu) in enumerate(level3_li, 1):
                            print(f"=={is_select3}, {num3}、{title3}, {jl}, {yu}")
                            tmp3 = {
                                "title": title3,
                                "title_number": num3,
                                "mode": 3 if is_select3 else -1,
                                "order": order3,
                                "jl": jl or {},
                                "yu": yu or {},
                                "children": []
                            }
                            tmp2["children"].append(tmp3)
                            if text3:
                                for op_order3, (op3, op_is_select3, jl, yu) in enumerate(self.get_op(text3), 1):
                                    print("op3", op_is_select3, op3, jl, yu)
                                    op_tmp3 = {
                                        "title": op3,
                                        "title_number": "",
                                        "mode": 3 if op_is_select3 else -1,
                                        "order": op_order3,
                                        "jl": jl or {},
                                        "yu": yu or {},
                                        "children": []
                                    }
                                    tmp3["children"].append(op_tmp3)

        return result

    def add_clear_ids(self):
        titles = [
            "没有变化", "没有以上症状，感觉正常", "没有加重或出现", "没有口腔溃疡"
        ]
        for obj in Question.objects.filter(title__in=titles):
            parent_obj = obj.parent
            Question.objects.filter(id__gt=parent_obj.id, id__lt=obj.id).update(clear_ids=[obj.id])
            cur_clear_ids = list(Question.objects.filter(id__gt=parent_obj.id, id__lt=obj.id).values_list("id", flat=1))
            Question.objects.filter(id=obj.id).update(clear_ids=cur_clear_ids)

    def check_jl_yu_level(self):
        data = {}
        for obj in Question.objects.all():
            jl = obj.jl
            if jl:
                data.setdefault("焦虑", {}).setdefault(jl["type"], {}).setdefault(jl["level"], 0)
                data["焦虑"][jl["type"]][jl["level"]] += 1

            yu = obj.yu
            if yu:
                data.setdefault("抑郁", {}).setdefault(yu["type"], {}).setdefault(yu["level"], 0)
                data["抑郁"][yu["type"]][yu["level"]] += 1

        for key, item in data.items():
            print(key)
            for key1, item1 in item.items():
                print(f"    {key1}")
                for key2, val in item1.items():
                    print(f"        {key2}: {val}")

    def handle(self, *args, **options):
        if not self.text:
            with open(os.path.join(BASE_DIR, "question", "qeustion_txt", "20250326.txt"), "r") as f:
                self.text = f.read()
        questions = self.parse_question()
        self.add_question(questions)
        # 添加clear_ids
        self.add_clear_ids()

        # self.check_jl_yu_level()


if __name__ == '__main__':
    Command().handle()
