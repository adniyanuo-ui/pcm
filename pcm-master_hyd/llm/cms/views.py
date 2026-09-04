import datetime
import json
import uuid

from llm.cms.serializers import (
    FormulaSearchRequestSerializer,
    ReviseSerializer,
    ShowChatSerializer,
    ShowChatOneSerializer,
)
from llm.models import Revise, Record
from llm_utils.client import model_name2client
from llm_utils.prompt import v1
from patient.models import Patient, Answer
from tools.resp import get_response
from tools.viewset import ModelViewSet
from django.http import StreamingHttpResponse
from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework import status

from llm_utils.rag import FormulaRetriever, RetrievalQuery


class ReviseView(ModelViewSet):
    http_method_names = ["post", "get"]
    queryset = Revise.objects.order_by("-star", "-id")
    serializer_class = ReviseSerializer

    def list(self, request, *args, **kwargs):
        pid = self.request.GET.get("pid")
        patient = Patient.objects.filter(id=pid).first()

        queryset = self.queryset.filter(p_id=patient.id)
        default_revise = Revise(p=patient, created_time=datetime.datetime.now())
        queryset = list(queryset) + [default_revise]
        serializer = self.get_serializer(queryset, many=True)
        return get_response(serializer.data, msg="数据获取成功")

    def create(self, request, *args, **kwargs):
        revise_id = request.data["revise_id"]

        star = request.data["star"]

        revise_output = request.data["revise_output"]

        revise = Revise.objects.filter(id=revise_id).first()
        Revise.objects.filter(id=revise.id).update(star=star, revise_output=revise_output)
        revise = Revise.objects.filter(id=revise_id).first()

        revise_li = [revise] + [Revise(p=revise.p, created_time=datetime.datetime.now())]
        serializer = self.get_serializer(revise_li, many=True)
        return get_response(data=serializer.data, msg="保存成功")


class FormulaSearchView(ModelViewSet):
    """返回有辞典原文和页码依据的候选基础方，不生成最终诊断或处方。"""

    http_method_names = ["get", "post"]

    @staticmethod
    def _retriever():
        return FormulaRetriever(settings.RAG_INDEX_PATH)

    def list(self, request, *args, **kwargs):
        try:
            metadata = self._retriever().metadata()
            safe_metadata = {
                key: metadata.get(key)
                for key in (
                    "schema_version",
                    "built_at",
                    "indexed_records",
                    "excluded_records",
                    "syndrome_terms",
                    "syndrome_links",
                    "corpus_sha256",
                )
            }
            return get_response({"ready": True, "index": safe_metadata})
        except FileNotFoundError:
            return get_response(
                {
                    "ready": False,
                    "message": "方剂索引尚未构建，请先执行 python manage.py build_fangji_index",
                }
            )

    def create(self, request, *args, **kwargs):
        serializer = FormulaSearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return get_response(
                code=400,
                msg=str(serializer.errors),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            query = RetrievalQuery.from_mapping(serializer.validated_data)
            result = self._retriever().search(query)
        except ValueError as exc:
            return get_response(
                code=400,
                msg=str(exc),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        except FileNotFoundError as exc:
            return get_response(
                code=503,
                msg=str(exc),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return get_response(result, msg="候选方检索完成")


class ChatView(ModelViewSet):
    # authentication_classes = []
    http_method_names = ["post"]

    @classmethod
    def gen(cls, uid, p_id, user, question, dialogue, doctor, model_name):
        uid = uid or 0

        messages = Revise.get_revise_output_msg(p_id, uid, user, question, dialogue, doctor)

        client = model_name2client[model_name]
        mark = f"{uuid.uuid4()}_{datetime.datetime.now()}"

        revise_id = 0
        for cur_output, cur_reasoning, record_id in Record.gen_llm_out(client, mark, model_name, messages):
            if revise_id == 0:
                revise_id = Revise.objects.create(
                    r_id=record_id, p_id=p_id, user=user, doctor=doctor, uid=uid, question=question, dialogue=dialogue
                ).id

            ret = {"output": cur_output, "reasoning": cur_reasoning, "revise_id": revise_id}
            line = f"{json.dumps(get_response(ret).data)}endendend".replace("\n\n", "\n")
            yield line

    def create(self, request, *args, **kwargs):
        p_id = request.data["patient_id"]
        user = request.data["user"]
        question = request.data["question"]
        dialogue = request.data["dialogue"]
        doctor = request.data["doctor"]
        model_name = request.data.get("model_name") or settings.DEFAULT_LLM_MODEL

        return StreamingHttpResponse(self.gen(request.user.id, p_id, user, question, dialogue, doctor, model_name),
                                     content_type="text/plain")


class ShowChatView(ModelViewSet):
    http_method_names = ["get"]
    queryset = Revise.objects.order_by("-id")
    serializer_class = ShowChatSerializer

    def get_queryset(self):
        if self.action != "list":
            return Record.objects.all()
        else:
            return self.queryset

    def get_serializer_class(self):
        if self.action != "list":
            return ShowChatOneSerializer
        else:
            return self.serializer_class


class GenDialogueView(ModelViewSet):
    http_method_names = ["post"]

    @classmethod
    def gen(cls, messages, model_name):
        client = model_name2client[model_name]
        mark = f"GenDialogue_{uuid.uuid4().hex}_{datetime.datetime.now()}"

        for cur_output, cur_reasoning, record_id in Record.gen_llm_out(client, mark, model_name, messages):
            ret = {"output": cur_output, "reasoning": cur_reasoning, "record_id": record_id}
            line = f"{json.dumps(get_response(ret).data)}endendend".replace("\n\n", "\n")
            yield line

    def create(self, request, *args, **kwargs):
        text = request.data["text"]
        model_name = request.data.get("model_name") or settings.DEFAULT_LLM_MODEL
        messages = [
            {'role': 'system', 'content': "帮我把以下文本以医患对话的方式展示出来。"},
            {'role': 'user', 'content': text}
        ]

        return StreamingHttpResponse(self.gen(messages, model_name), content_type="text/plain")


class GaseView(ModelViewSet):
    http_method_names = ["post", "put"]

    def update(self, request, *args, **kwargs):
        revise_id = kwargs["pk"]
        revise_case = request.data["revise_case"]
        Revise.objects.filter(id=revise_id).update(revise_case=revise_case)
        return get_response(msg="更新成功")

    @classmethod
    def gen(cls, messages, model_name, revise_id):
        client = model_name2client[model_name]
        mark = f"Case_{uuid.uuid4().hex}_{datetime.datetime.now()}"

        case = ""
        for cur_output, cur_reasoning, record_id in Record.gen_llm_out(client, mark, model_name, messages):
            ret = {"output": cur_output, "reasoning": cur_reasoning, "record_id": record_id}
            case += cur_output
            line = f"{json.dumps(get_response(ret).data)}endendend".replace("\n\n", "\n")
            yield line

        Revise.objects.filter(id=revise_id).update(case=case, revise_case=case)

    def create(self, request, *args, **kwargs):
        revise_id = request.data["revise_id"]
        user = request.data["user"]
        # question = request.data["question"]
        dialogue = request.data["dialogue"]
        doctor = request.data["doctor"]
        revise_output = request.data["revise_output"]
        if not revise_output:
            return APIException("还未生成AI辅助诊疗方案")

        Revise.objects.filter(id=revise_id).update(revise_output=revise_output)
        model_name = request.data.get("model_name") or settings.DEFAULT_LLM_MODEL

        user_content = f"""
患者基本信息：
{user}


医患对话信息：
{dialogue}


医生面诊信息：
{doctor}


辅助诊疗方案：
{revise_output}
"""
        messages = [
            {'role': 'system', 'content': """**任务**：根据患者前述诊疗过程和结果，生成一份标准的中医门诊病历，要求实用、真实，并满足卫健委和医保飞行检查要求。

---

### 一、核心要求

1. **格式规范**：严格按照《中医病历书写基本规范》要求，包含所有必备字段
2. **内容真实**：基于患者实际症状、诊疗过程和结果，不虚构、不遗漏
3. **逻辑完整**：体现中医辨证论治的完整思路（理法方药一致）
4. **检查合规**：满足卫健委、医保局飞行检查标准，重点字段无缺失

---

### 二、病历结构要求

请按以下结构生成病历，每个模块的字段不可遗漏：

#### （一）基本信息
- 就诊时间（精确到分钟）
- 就诊科别
- 患者姓名、性别、年龄、民族、婚姻状况、职业
- 药物过敏史
- 常住地址
- 联系电话

#### （二）主诉
- 格式：主要症状 + 持续时间（如“情绪不稳伴失眠、乏力2年余，加重1个月”）

#### （三）现病史
- 疾病发生、演变过程
- 诊疗经过（如有）
- 当前主要症状（分类描述：全身状态、精神情志、头面五官、消化系统、二便、睡眠、肢体动作等）

#### （四）中医四诊情况
| 诊法 | 具体内容 |
|------|---------|
| 望诊 | 神色、形态、舌象（舌质、舌苔、舌体） |
| 闻诊 | 语声、气息、气味 |
| 问诊 | （可引用现病史内容，注明“详见现病史”） |
| 切诊 | 脉象、其他切诊发现 |

#### （五）体格检查
- 生命体征（T、P、R、BP）
- 各系统针对性检查阳性体征
- 必要的阴性体征

#### （六）辅助检查
- 检验、检查结果（若无，注明“患者自述近期医学检查结果正常，未提供具体报告”）

#### （七）诊断
**中医诊断**（必须包含疾病诊断 + 证候诊断）：
1. 疾病名 + 证型（如“郁病 肝郁脾虚，胆热痰扰证”）
2. 合并病可分行列出

**西医诊断**：
1. 对应西医病名（如“焦虑状态”“失眠症”等）

#### （八）辨证论治依据（理法方药一致性说明）
- **病机分析**：说明病因、病位、病性、病势，解释证候形成机理
- **治法**：明确治疗原则
- **方药**：完整处方（含剂量、用法）
- **方解**：君臣佐使分析，解释为何此方对应该病机

#### （九）医嘱
- **饮食宜忌**：具体可执行的建议
- **作息建议**：睡眠、活动、放松指导
- **舌象观察**：改善标志、观察方法（增强患者参与感）
- **心理疏导**：共情式话术示例（可选）
- **复诊建议**：何时复诊、重点反馈什么

#### （十）医师签名
- 接诊医师签名
- 日期

---"""},
            {'role': 'user', 'content': user_content}
        ]

        return StreamingHttpResponse(self.gen(messages, model_name, revise_id), content_type="text/plain")
