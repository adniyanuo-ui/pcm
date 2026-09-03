import datetime
import json

import requests
from django.shortcuts import render

# Create your views here.
from patient.mobile.serializers import PatientSerializer, HistorySerializer, HistoryRetrieveSerializer
from patient.models import Patient, Answer, People
from pcm.settings import code2session_url, app_id, app_secret
from question.models import Question
from tools.resp import get_response
from tools.token_util import token
from tools.viewset import ModelViewSet
from patient.management.commands.to_pdf import Command as ToPdfCommand
from llm.task import gen_prescription


class LoginView(ModelViewSet):
    http_method_names = ["post"]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        code = request.data["code"]

        resp = requests.get(
            code2session_url,
            params={"js_code": code, "appid": app_id, "secret": app_secret, "grant_type": "authorization_code"}
        )
        data = resp.json()
        openid = data["openid"]

        obj, _ = People.objects.update_or_create(
            openid=openid,
        )
        t = token.encode({"user_id": obj.id}, key="mobile")
        People.objects.filter(id=obj.id).update(token=t)

        return get_response({"token": t})


class PatientView(ModelViewSet):
    http_method_names = ["post", "get"]
    queryset = Patient.objects
    serializer_class = PatientSerializer

    def list(self, request, *args, **kwargs):
        result = {}

        user = self.request.user
        q_type = self.request.GET.get("q_type", "common")
        obj = self.queryset.filter(people_id=user.id, q_type=q_type).order_by("-id").first()
        if not obj:
            obj = self.queryset.filter(people_id=user.id).order_by("-id").first()

        if obj:
            serializer = self.get_serializer(obj)
            result = serializer.data

        return get_response(result, msg="数据获取成功")

    def create(self, request, *args, **kwargs):
        user = request.user

        name = request.data["name"]
        sex = request.data["sex"]
        age = request.data["age"]
        date = request.data["date"]

        q_type = request.data.get("q_type", "common")

        height = request.data.get("height", "")
        weight = request.data.get("weight", "")
        blood_type = request.data.get("blood_type", "")
        blood_sugar = request.data.get("blood_sugar", "")
        blood_pressure = request.data.get("blood_pressure", "")
        phone = request.data.get("phone", "")

        marital_status = request.data.get("marital_status", "")
        job = request.data.get("job", "")
        origin = request.data.get("origin", "")

        company = request.data.get("company", "")
        department = request.data.get("department", "")

        date = f"{date} {datetime.datetime.now().__str__().rsplit(' ', 1)[-1]}"
        obj = Patient.objects.create(
            people_id=user.id, q_type=q_type, name=name, sex=sex, age=age, date=date, phone=phone,
            marital_status=marital_status, job=job, origin=origin, height=height, weight=weight, blood_type=blood_type,
            blood_sugar=blood_sugar, blood_pressure=blood_pressure, company=company, department=department
        )

        return get_response({"patient_id": obj.id})


class AnswerView(ModelViewSet):
    http_method_names = ["post"]

    def create(self, request, *args, **kwargs):
        patient_id = request.data["patient_id"]
        q_id = request.data["q_id"]
        answer = request.data["answer"]
        # for key in answer:
        #     answer[key] = True

        Answer.objects.update_or_create(
            p_id=patient_id, q_id=q_id, defaults={
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
        # user = request.user
        # user = Patient.objects.filter(id=32).first()
        patient_id = request.data["patient_id"]
        doctor_id = int(request.data.get("doctor_id", "0") or "0")

        patient = Patient.objects.filter(id=patient_id).first()
        if patient.result:
            return get_response(patient.result)

        q_id2q = {x.id: x for x in Question.objects.all()}

        score_data = {
            "jl": {},  # level: {之一:[分数], 定性: [分数]}  基础分加一得最终分，取最高分
            "yu": {},
        }
        for obj in Answer.objects.filter(p_id=patient_id).values_list("q_id", "all_answer", named=1):
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
        Patient.objects.filter(id=patient_id).update(
            result=result_str, jl_score=data["jl"], jl_level=result["jl"], yu_score=data["yu"], yu_level=result["yu"],
            doctor_id=doctor_id
        )
        ToPdfCommand().handle(p_id=patient_id)
        gen_prescription.apply_async((patient_id,))
        return get_response(result_str)


class HistoryView(ModelViewSet):
    http_method_names = ["get"]
    queryset = Patient.objects
    serializer_class = HistorySerializer

    def get_queryset(self):
        return self.queryset.filter(people_id=self.request.user.id, history_show=True)

    def get_serializer_class(self):
        if self.action != "list":
            return HistoryRetrieveSerializer
        return self.serializer_class
