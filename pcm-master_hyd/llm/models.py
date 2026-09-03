import json
import time

from django.db import models

# Create your models here.
from django.db import models

# Create your models here.
from llm_utils.prescription import prescription
from patient.models import Patient, Answer
from tools.base_model import BaseModel


class Record(BaseModel):
    mark = models.CharField(verbose_name="每个请求一个标记", default="", max_length=255, unique=True)
    model_name = models.CharField(verbose_name="模型", default="", max_length=256)

    runtime = models.FloatField(verbose_name="运行时间(s)", default=0.0)
    prompt_tokens = models.IntegerField(verbose_name="问的token数量", default=0)
    completion_tokens = models.IntegerField(verbose_name="回答token数量", default=0)

    messages = models.TextField(verbose_name="问大模型的参数", default="")
    output = models.TextField(verbose_name="大模型的输出", default="")
    reasoning = models.TextField(verbose_name="大模型的思考", default="")

    err = models.BooleanField(verbose_name="是否报错", default=False)
    err_msg = models.TextField(verbose_name="报错信息", default="")

    class Meta:
        verbose_name = "大模型问答记录"

    @classmethod
    def gen_llm_out_stream(cls, completion, record, start_time):
        output = ""
        reasoning = ""

        chat_completion_json = None
        for chat_completion in completion:
            chat_completion_json = json.loads(chat_completion.model_dump_json())
            cur_reasoning = ""
            cur_output = ""
            for choice in chat_completion_json["choices"]:
                cur_output += (choice["delta"]["content"] or "")
                cur_reasoning += (choice["delta"].get("reasoning_content", "") or "")

            output += cur_output
            reasoning += cur_reasoning
            yield cur_output, cur_reasoning, record.id

        prompt_tokens = chat_completion_json["usage"]["prompt_tokens"]
        completion_tokens = chat_completion_json["usage"]["completion_tokens"]

        runtime = round(time.time() - start_time, 2)
        Record.objects.filter(id=record.id).update(
            runtime=runtime, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, output=output,
            reasoning=reasoning
        )

    @classmethod
    def gen_llm_out(cls, client, mark, model_name, messages, stream=True, **kwargs):
        record = Record.objects.create(
            mark=mark, messages=json.dumps(messages, ensure_ascii=False), model_name=model_name,
        )
        try:
            start_time = time.time()

            if stream:
                kwargs["stream_options"] = {"include_usage": True}

            completion = client.chat.completions.create(
                model=model_name, messages=messages, stream=stream, **kwargs
            )

            if not stream:
                completion_json = json.loads(completion.model_dump_json())
                output = completion_json['choices'][0]['message']['content']
                reasoning = completion_json['choices'][0]['message'].get("reasoning_content", "")
                prompt_tokens = completion_json['usage']['prompt_tokens']
                completion_tokens = completion_json['usage']['completion_tokens']

                runtime = round(time.time() - start_time, 2)

                Record.objects.filter(id=record.id).update(
                    runtime=runtime, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, output=output,
                    reasoning=reasoning
                )
                return Record.objects.filter(id=record.id).first()
            else:
                return cls.gen_llm_out_stream(completion, record, start_time)
        except Exception as e:
            Record.objects.filter(id=record.id).update(err=True, err_msg=f"llm err: {e}")
            raise e


class Revise(BaseModel):
    r = models.OneToOneField(Record, on_delete=models.CASCADE, related_name="revise")
    p = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="revise")

    user = models.TextField(verbose_name="用户基本信息", default="")
    question = models.TextField(verbose_name="用户问卷调查", default="")
    dialogue = models.TextField(verbose_name="医患对话", default="")
    doctor = models.TextField(verbose_name="医生部分的输入", default="")

    revise_output = models.TextField(verbose_name="人工修正的输出", default="")

    case = models.TextField(verbose_name="病历输出", default="")
    revise_case = models.TextField(verbose_name="人工修正的病历输出", default="")

    prescription = models.TextField(verbose_name="推荐的处方", default="")
    # -1 表示没有进行星级打分
    star = models.IntegerField(verbose_name="星级", default=-1)

    uid = models.IntegerField(verbose_name="请求的用户", default=0)

    class Meta:
        verbose_name = "针对患者的模型输出进行追加修改"

    @classmethod
    def init_user(cls, patient):
        user_info = {
            "姓名": patient.name,
            "性别": patient.sex,
            "年龄": patient.age,
            "联系方式": patient.phone,
            # "身高cm": patient.height,
            # "体重kg": patient.weight,
            "婚姻状况": patient.marital_status,
            "职业": patient.job,
            "住址": patient.origin,
            "出生年月": patient.birthday,
            "民族": patient.nation,
            "药物过敏史": patient.allergy,
        }
        user_info = ";    ".join([f"{k}: {v}" for k, v in user_info.items() if v])
        return user_info

    @classmethod
    def init_question(cls, patient):
        answer = []
        for questions in Answer.gen_questions(patient.id):
            for question in questions:
                blank = f" " * question["level"] * 4
                title_number = ""
                if question['title_number']:
                    title_number = f"{question['title_number']}、"

                if title_number or question['title']:
                    answer.append(f"{blank}{title_number}{question['title']}")

                if question['mode'] == 2:
                    answer.append(f"{blank * 2}{question['an']}")
        answer = "\n".join(answer)
        return answer

    @classmethod
    def init_doctor(cls, patient):
        return ""

    @classmethod
    def init_dialogue(cls, patient):
        return ""

    @classmethod
    def init_revise_case(cls, patient):
        return ""

    @classmethod
    def get_inp(cls, user, question, dialogue, doctor):
        inp = f"""用户: {user}
问卷: 
{question}
医患对话:
{dialogue}
"""
        if doctor:
            inp += f"\n大夫: {doctor}"

        return inp

    @classmethod
    def get_examples(cls, uid=0):
        result = ""

        examples_li = []
        for n, obj in enumerate(Revise.objects.filter(uid=uid, star=5).order_by("-id")[:5], 1):
            cur_inp = Revise.get_inp(obj.user, obj.question, obj.dialogue, obj.doctor)
            tmp = []
            for x in ["输入: "] + cur_inp.split("\n") + ["输出: "] + obj.revise_output.split("\n"):
                tmp.append(f"{x}")
            examples_li.append(f"示例{n}: " + "\n".join(tmp))

        if examples_li:
            s = '\n\n'.join(examples_li)
            result = f"- Examples: \n{s}"

        return result

    @classmethod
    def get_revise_output_msg(cls, patient_id, uid=0, user=None, question=None, dialogue=None, doctor=None,
                              get_user=False, system=""):
        patient = Patient.objects.filter(id=patient_id).first()

        if user is None: user = Revise.init_user(patient)
        if question is None: question = Revise.init_question(patient)
        if doctor is None: doctor = Revise.init_doctor(patient)
        if dialogue is None: dialogue = Revise.init_dialogue(patient)
        system = system or f"""---

```
请严格遵循以下中医辨证论治思维链，对患者进行完整诊断。每一步必须说明推理依据，确保可解释性，让大夫清楚“为什么这样判断、为什么开这个方”。

---

### 第1步：四诊合参——收集信息
请从问卷和问诊记录中提取关键症状与体征，整理为标准化术语。
【示例输出格式】
- 全身状态：乏力、怕冷
- 消化系统：纳差、便溏
- 面色舌象：面色萎黄、舌淡苔白、舌体胖大
- 脉象：脉沉细弱

---

### 第2步：辨证分析——抓病机（核心环节）
请从以下四个维度进行综合分析，每一维度需给出推理过程。

| 辨证维度 | 推理过程（结合症状说明） | 结论 |
|---------|----------------------|------|
| 六经辨证 | 根据症状逐一排除：无发热恶寒→非太阳；无口苦咽干→非少阳；无但欲寐→非少阴；结合纳差便溏→考虑太阴病 | 太阴病 |
| 八纲辨证 | 乏力、怕冷→虚证、寒证；病程长、脏腑症状→里证 | 里虚寒证 |
| 脏腑辨证 | 乏力、纳差、便溏→脾；怕冷、脉沉→肾 | 脾肾阳虚 |
| 气血津液 | 舌淡、脉弱→气虚；面色萎黄→血虚 | 气虚血弱 |

【综合病机推理】
请结合以上分析，完整描述病机（含病因、病位、病性、病势、证候）：
示例：脾肾阳虚，运化失职则纳差便溏；温煦无权则怕冷；气血生化不足则乏力、面色萎黄、脉弱。

【证型诊断】
示例：脾肾阳虚证，兼气血不足

---

### 第3步：确立治法——以法统方
请根据病机推导治法，并说明对应关系。

| 病机要素 | 对应治法原则 | 具体治法 |
|---------|-------------|---------|
| 脾肾阳虚 | 温补 | 温补脾肾 |
| 气血不足 | 补益 | 益气养血 |

【综合治法】
示例：温补脾肾，益气养血（说明：温补脾肾以复运化温煦之功，益气养血以充气血亏虚之体）

---

### 第4步：选方遣药——方从法出

【选主方（骨架）】
请说明选择依据，包括方剂出处和对应关系：
- 温补脾肾：可选附子理中汤（《伤寒论》温脾要方）或右归丸（《景岳全书》温肾要方）
- 益气养血：可选八珍汤（《正体类要》气血双补基础方）
- 综合考量：患者以脾虚症状（纳差便溏）为主，故先以附子理中汤温脾，加补肾药兼顾肾阳

【加减化裁（添血肉）】
请结合患者具体症状说明加减理由：
- 加黄芪：增强补气之力，针对乏力明显
- 加当归：养血活血，针对面色萎黄、血虚
- 加杜仲：补肾强腰，针对怕冷、脉沉（肾阳不足）

【剂量考量】
请说明剂量调整原则：
- 附子先煎减毒，9g为温阳常用起始剂量
- 黄芪重用20g以强补气之功
- 余药按常规剂量，根据体质平和调整

---

### 第5步：写出方剂

请以规范格式输出完整处方，并附简要方解：

```
【处方】
附子理中汤加减：
制附子9g（先煎）、党参15g、炒白术12g、干姜6g、炙甘草6g
黄芪20g、当归12g、杜仲15g
水煎服，每日一剂

【方解】
- 附子配干姜：温补脾肾之阳，为君
- 党参、白术、炙甘草：益气健脾，助运化，为臣
- 黄芪：增强补气之力
- 当归：养血和血
- 杜仲：补肾强腰
全方温补脾肾为主，兼益气养血，针对脾肾阳虚、气血不足之证。
```

---

### 第6步：身心同治——医嘱与康复指导

【饮食宜忌】
- 宜吃：温热易消化食物，如小米粥、山药、南瓜、生姜、红枣、羊肉汤（少量）
- 忌吃：生冷寒凉（冰饮、凉菜、西瓜）、油腻黏滞（糯米、肥肉）、难消化食物

【作息建议】
- 保证充足睡眠，尽量晚上11点前入睡（子时养阳）
- 白天适度活动，如散步、八段锦，忌大汗淋漓
- 注意保暖，尤其腰腹、后背（督脉、肾所在）

【舌象观察（增强参与感）】
- 改善标志：舌苔由白厚→变薄白，舌体胖大→逐渐收小，舌色由淡白→转淡红
- 观察建议：每周晨起拍照一次，对比变化，复诊时可带舌象记录供大夫参考

【复诊建议】
- 服药7剂后复诊，根据症状变化和舌象调整方案

【心理按摩（话术示例）】
根据患者体质和情绪特点，给予共情式心理疏导，增强治疗信心：
- 示例：“您这病主要是脾肾阳气不足，好比身体的‘火力’不够了，所以怕冷、没劲、消化不好。咱们用药就是帮您把‘火’慢慢烧旺，同时补上气血。这个过程需要一点耐心，但方向对了，身体会一天天感觉不一样。平时别太操劳，也别给自己太大压力，心情放松了，阳气恢复得才快。”

---

**核心要求**：确保推理链条完整可追溯，让使用者清楚理解诊断和处方依据。最后一步体现“身心同治”理念，提升患者配合度和康复信心。
```"""

        inp = Revise.get_inp(user, question, dialogue, doctor)
        examples = Revise.get_examples(uid)
        if examples:
            inp += f"\n\n{examples}"

        messages = [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': inp}
        ]
        if get_user:
            return messages, user, question, doctor
        else:
            return messages
