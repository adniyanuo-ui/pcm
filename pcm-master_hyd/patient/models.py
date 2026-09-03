from django.db import models

from question.models import Question
from tools.base_model import BaseModel


class People(BaseModel):
    # 手机号/小程序id
    openid = models.CharField(verbose_name="唯一标识", max_length=255, unique=True, blank=True, null=True)

    # 通过授权获取的这个的优先级最高
    phone = models.CharField(verbose_name="手机号", default="", max_length=32)
    nick_name = models.CharField(verbose_name="微信昵称", max_length=1024, default="")
    avatar_url = models.CharField(verbose_name="头像", max_length=1024, default="")

    password = models.CharField(verbose_name="密码", max_length=1024, default="")

    token = models.CharField(max_length=256, default="")

    class Meta:
        verbose_name = "用户唯一标识"


class Patient(BaseModel):
    # 患者的 姓名、性别、年龄、就诊日期为必填项
    """
姓名：            性别：       年龄：     电话：
婚育状况（未婚 / 已婚 / 离异 / 丧偶）     职业：
籍贯：
就诊日期：
"name": "",
"sex": "",
"age": "",
"height": "",
"weight": "",
"phone": "",
"marital_status": "",
"job": "",
"origin": "",
"date": moment().format('YYYY-MM-DD'),

"blood_type": "",
"blood_sugar": "",
"blood_pressure": "",
    """
    sex_choice = [
        ("男", "男"),
        ("女", "女"),
    ]
    marital_status_choice = [
        ("未婚", "未婚"),
        ("已婚", "已婚"),
        ("离异", "离异"),
        ("丧偶", "丧偶"),
    ]
    q_type_choice = [
        ("common", "通用"),
        ("school", "学校"),
        ("company", "企业"),
        ("gov", "机关单位"),
    ]
    people = models.ForeignKey(People, on_delete=models.CASCADE, related_name="patient", blank=True, null=True)

    q_type = models.CharField(verbose_name="问卷类型", default="common", max_length=32)

    name = models.CharField(verbose_name="姓名", default="", max_length=256)
    # 女/男
    sex = models.CharField(verbose_name="性别", default="男", max_length=32, choices=sex_choice)
    age = models.IntegerField(verbose_name="年龄", default=0)
    date = models.DateTimeField(verbose_name="就诊日期")
    height = models.CharField(verbose_name="身高cm", default="", max_length=32)
    weight = models.CharField(verbose_name="体重kg", default="", max_length=32)
    phone = models.CharField(verbose_name="手机号", default="", max_length=32)
    marital_status = models.CharField(verbose_name="婚姻状况", default="", max_length=32, choices=marital_status_choice)

    job = models.CharField(verbose_name="职业", default="", max_length=256)
    origin = models.CharField(verbose_name="长期居住地", default="", max_length=256)
    blood_type = models.CharField(verbose_name="血型", default="", max_length=256)
    blood_sugar = models.CharField(verbose_name="血糖", default="", max_length=256)
    blood_pressure = models.CharField(verbose_name="血压", default="", max_length=256)

    birthday = models.CharField(verbose_name="出生年月", default="", max_length=256)
    nation = models.CharField(verbose_name="民族", default="", max_length=256)
    allergy = models.CharField(verbose_name="药物过敏史", default="", max_length=256)

    company = models.CharField(verbose_name="企业/学校", default="", max_length=256)
    department = models.CharField(verbose_name="部门/院系", default="", max_length=256)

    # 废弃
    # token = models.CharField(max_length=256, default="")

    jl_score = models.FloatField(verbose_name="焦虑分数", default=0.0)
    jl_level = models.IntegerField(verbose_name="焦虑等级", default=0)

    yu_score = models.FloatField(verbose_name="抑郁分数", default=0.0)
    yu_level = models.IntegerField(verbose_name="抑郁等级", default=0)

    result = models.CharField(verbose_name="结果", default="", max_length=1024)
    # 不需要 {id}.pdf 就是
    file = models.CharField(verbose_name="答题详情文件", default="", max_length=1024)

    history_show = models.BooleanField(verbose_name="是否在历史问卷中展示", default=False)

    doctor_id = models.IntegerField(verbose_name="医生id", default=0)

    class Meta:
        verbose_name = "患者"
        indexes = [
            models.Index(fields=['phone', 'name'], name='pn'),
        ]


class Answer(BaseModel):
    # 每一道题对应一个屏幕的答案
    p = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="answer")
    q_id = models.IntegerField(verbose_name="对应的level1题目id", default=0)

    answer = models.IntegerField(verbose_name="题目的答案", default=0)
    # {id: 0/1}
    all_answer = models.JSONField(verbose_name="所有答案", default=dict)
    # {parent_id: op_id}
    op_radio_answer = models.JSONField(verbose_name="选项的答案", default=dict)
    # {parent_id-op_id: text}
    op_input_answer = models.JSONField(verbose_name="填写的答案", default=dict)

    class Meta:
        verbose_name = "答卷"
        indexes = [
            models.Index(fields=['p', 'q_id'], name='pq'),
        ]

    @classmethod
    def gen_questions(cls, patient_id):
        id2question = Question.get_all_question()

        ignore_ids = []
        for obj in Answer.objects.filter(p_id=patient_id).order_by("q_id"):
            all_answer = obj.all_answer
            questions = []
            for q_id, q_an in all_answer.items():
                if not q_an:
                    continue

                q_id = int(q_id)
                if q_id not in id2question:
                    continue

                q_item = id2question[q_id]
                if q_item["mode"] == -1:
                    continue

                if q_item["title"] in [
                    "没有变化", "没有以上症状，感觉正常", "没有加重或出现", "没有口腔溃疡"
                ]:
                    continue

                if q_item["mode"] == 2:
                    q_item["an"] = q_an
                else:
                    q_item["an"] = "√"

                questions.append(q_item)
                title_ignore = [q_item["title"]]
                for parent_q_id in q_item["parent"].split("-"):
                    parent_q_id = int(parent_q_id)
                    if parent_q_id == 0:
                        continue

                    if parent_q_id in ignore_ids:
                        continue
                    ignore_ids.append(parent_q_id)

                    parent_item = id2question[parent_q_id]
                    if parent_item["title"] not in ["", "其他症状", *title_ignore]:
                        questions.append(parent_item)
                        title_ignore.append(parent_item["title"])

            questions = sorted(questions, key=lambda x: [int(x) for x in x["parent"].split("-")] + [x["id"]])
            yield questions
