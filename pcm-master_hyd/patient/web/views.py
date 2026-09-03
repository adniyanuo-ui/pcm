import datetime
import hashlib
import json
import time
import uuid

from django.shortcuts import render

from patient.web.filters import PatientFilter
from patient.web.serializers import PatientSerializer
# Create your views here.
from patient.models import Patient, Answer, People
from question.models import Question
from tools.resp import get_response
from tools.token_util import token
from tools.viewset import ModelViewSet
from patient.management.commands.to_pdf import Command as ToPdfCommand
from django.db import transaction


class PatientView(ModelViewSet):
    http_method_names = ["post", "get"]
    authentication_classes = []
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    filterset_class = PatientFilter

    def list(self, request, *args, **kwargs):
        name = request.GET.get("name")
        phone = request.GET.get("phone")
        if not phone or not name:
            return get_response({})

        resp = super().list(request, *args, **kwargs)
        data = resp.data["data"]
        result = {}
        if data:
            result = data[0]
        return get_response(result)

    def create(self, request, *args, **kwargs):
        name = request.data["name"]
        sex = request.data.get("sex", "")
        age = request.data.get("age", 0) or 0
        date = request.data.get("date") or datetime.datetime.now()
        phone = request.data.get("phone", "")
        password = request.data.get("password", "").strip() or "123456"

        doctor_id = request.data.get("doctor_id", "0") or "0"
        height = request.data.get("height", "")
        weight = request.data.get("weight", "")
        birthday = request.data.get("birthday", "")
        nation = request.data.get("nation", "")
        allergy = request.data.get("allergy", "")
        # blood_type = request.data.get("blood_type", "")
        # blood_sugar = request.data.get("blood_sugar", "")
        # blood_pressure = request.data.get("blood_pressure", "")

        marital_status = request.data.get("marital_status", "")
        job = request.data.get("job", "")
        origin = request.data.get("origin", "")

        with transaction.atomic(using=People.objects.db):
            people, _ = People.objects.update_or_create(openid=phone, defaults=dict(nick_name=name, password=password))
            Patient.objects.create(
                people_id=people.id, name=name, sex=sex, age=age, date=date, phone=phone, marital_status=marital_status,
                job=job, origin=origin, height=height, weight=weight, birthday=birthday, nation=nation, allergy=allergy,
                doctor_id=doctor_id
            )

        t = token.encode({"user_id": people.id, "name": people.nick_name}, datetime.timedelta(hours=12))
        People.objects.filter(id=people.id).update(token=t)

        return get_response({"uid": people.id, "name": name, "token": t})


class LoginView(ModelViewSet):
    http_method_names = ["post"]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        username = request.data["username"]
        password = request.data["password"].strip()
        people = People.objects.filter(openid=username).first()
        if not people:
            return get_response(code=401, msg="未注册的手机号")

        if people.password != password:
            return get_response(code=401, msg="密码错误")

        now = datetime.datetime.now()
        last_patient = Patient.objects.filter(people_id=people.id).order_by("-id").first()
        Patient.objects.create(
            people_id=people.id, name=last_patient.name, sex=last_patient.sex, age=last_patient.age,
            date=now, phone=last_patient.phone, marital_status=last_patient.marital_status,
            job=last_patient.job, origin=last_patient.origin, height=last_patient.height, weight=last_patient.weight
        )

        t = token.encode({"user_id": people.id, "name": people.nick_name}, datetime.timedelta(hours=12))
        People.objects.filter(id=people.id).update(token=t)

        return get_response({"uid": people.id, "name": people.nick_name, "token": t})


class AnswerView(ModelViewSet):
    http_method_names = ["post"]

    def list(self, request, *args, **kwargs):
        patient = request.user
        question_id = request.GET["question_id"]

        result = {}
        answer = Answer.objects.filter(p_id=patient.id, q_id=question_id) \
            .values_list("answer", "op_radio_answer", "op_input_answer", named=1).first()
        if answer:
            result["answer"] = answer.answer
            result["op_radio_answer"] = answer.op_radio_answer
            result["op_input_answer"] = answer.op_input_answer

        return get_response(result)

    def get_all_answer(self, question: list) -> dict:
        result = {}
        for item in question:
            result[item["id"]] = int(item.get("answer", 0))
            result.update(self.get_all_answer(item.get("children", [])))
        return result

    def create(self, request, *args, **kwargs):
        patient = request.user
        q_id = request.data["q_id"]
        answer = request.data["answer"]
        # for key in answer:
        #     answer[key] = True

        Answer.objects.update_or_create(
            p_id=patient.id, q_id=q_id, defaults={
                "all_answer": answer
            }
        )
        return get_response(msg="做题成功")


class ResultView(ModelViewSet):
    http_method_names = ["post"]
    # authentication_classes = []
    dx_level2score = {
        0: 0,
        1: 3,
        2: 6,
        3: 9,
        4: 12,
        5: 15,
        6: 18,
        7: 21,
        8: 24,
        9: 27,
        10: 30,
    }
    zy_level2score = {
        0: 0,
        1: 1,
        2: 4,
        3: 7,
        4: 10,
        5: 13,
        6: 16,
        7: 19,
        8: 22,
        9: 25,
        10: 28,
    }
    jl_yu_level2scores = {
        1: [0, 5],
        2: [5, 8],
        3: [8, 11],
        4: [11, 14],
        5: [14, 17],
        6: [17, 20],
        7: [20, 23],
        8: [23, 26],
        9: [26, 29],
        10: [29, 100000],
    }

    def create(self, request, *args, **kwargs):
        user = request.user
        # user = Patient.objects.filter(id=32).first()

        q_id2q = {x.id: x for x in Question.objects.all()}

        score_data = {
            "jl": {},  # level: {之一:[分数], 定性: [分数]}  基础分加一得最终分，取最高分
            "yu": {},
        }
        for obj in Answer.objects.filter(p_id=user.id).values_list("q_id", "all_answer", named=1):
            for q_id, is_select in obj.all_answer.items():
                if not is_select:
                    continue

                q = q_id2q[int(q_id)]
                if q.mode == -1:
                    continue

                for key, item in score_data.items():
                    jl_or_yu = getattr(q, key, {})
                    if not jl_or_yu:
                        continue

                    if jl_or_yu["type"] == "之一":
                        score = self.zy_level2score[jl_or_yu["level"]]
                    else:
                        score = self.dx_level2score[jl_or_yu["level"]]

                    score_data[key].setdefault(jl_or_yu["level"], {}).setdefault(jl_or_yu["type"], []).append(score)

        data = {
            "jl": 0,
            "yu": 0,
        }
        level0 = {
            "jl": 0,
            "yu": 0,
        }
        for key, item in score_data.items():
            nmx = {
                "n": 0,
                "m": 0,
                "x": 0,
            }
            for level, item1 in item.items():
                if level == 0:
                    level0[key] = (0.3 * len(item1["定性"]))
                    continue

                li = []
                for scores in item1.values():
                    li.append(scores[0] + len(scores) - 1)

                max_score = max(li)
                nmx["n"] += max_score
                nmx["m"] += self.dx_level2score[level]
                if nmx["x"] < max_score:
                    nmx["x"] = max_score

            if nmx["m"] == 0:
                data[key] = 0
            else:
                data[key] = nmx["n"] / nmx["m"] * nmx["x"]

        if level0["jl"] == level0["yu"]:
            data["jl"] += level0["jl"]
            data["yu"] += level0["yu"]
        elif level0["jl"] > level0["yu"]:
            data["jl"] += sum(level0.values())
        else:
            data["yu"] += sum(level0.values())

        result = {
            "jl": 0,
            "yu": 0,
        }
        for key, score in data.items():
            for level, (min_score, max_score) in self.jl_yu_level2scores.items():
                if min_score < score <= max_score:
                    result[key] = level
                    break

        # A10B5
        result_str = f"焦虑{result['jl']}级(A{result['jl']})     抑郁{result['yu']}级(B{result['yu']})。"
        Patient.objects.filter(id=user.id).update(
            result=result_str, jl_score=data["jl"], jl_level=result["jl"], yu_score=data["yu"], yu_level=result["yu"]
        )
        ToPdfCommand().handle(p_id=user.id)
        return get_response(result_str)
