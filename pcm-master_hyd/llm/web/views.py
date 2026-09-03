import datetime
import json
import uuid

from llm.cms.serializers import ReviseSerializer, ShowChatSerializer, ShowChatOneSerializer
from llm.models import Revise, Record
from llm_utils.client import model_name2client
from llm_utils.prompt import v1
from patient.models import Patient, Answer
from tools.resp import get_response
from tools.viewset import ModelViewSet
from django.http import StreamingHttpResponse


class MedicalRecordView(ModelViewSet):
    authentication_classes = []
    http_method_names = ["post"]
    tmp = f"""### **中医门诊病历**

**基本情况**

---

**四诊信息**

---

**辨证分析**

---

**治疗法则**

---

**医嘱**

---

**医师签名：** [您的姓名/机构名]
**（盖章）**"""

    @classmethod
    def gen(cls, chat_history, model_name):
        client = model_name2client[model_name]
        mark = f"medical/record_{uuid.uuid4().hex}_{datetime.datetime.now()}"
        messages = [
            {'role': 'system',
             'content': f"你是一名经验丰富的老中医，根据病人上述症状，生成中医门诊病历。下面是病历模版：\n{cls.tmp}"},
            {'role': 'user', 'content': chat_history}
        ]

        for cur_output, cur_reasoning, record_id in Record.gen_llm_out(client, mark, model_name, messages):
            ret = {"output": cur_output, "reasoning": cur_reasoning, "record_id": record_id}
            line = f"{json.dumps(get_response(ret).data)}endendend".replace("\n\n", "\n")
            yield line

    def create(self, request, *args, **kwargs):
        chat_history = request.data["chat_history"]
        model_name = request.data["model_name"]

        return StreamingHttpResponse(self.gen(chat_history, model_name), content_type="text/plain")
