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
    十七 既往病史与治疗
1. 您既往是否患过重大疾病？（如心脏病、中风、肝炎、肾炎等）若有，请说明疾病名称、患病时间及治疗情况。
    A. 无重大疾病史
    B. 有，具体为：___________，患病时间___________，治疗情况___________
2. 目前是否正在接受其他治疗或服用药物？（包括中药、西药、保健品等）请详细说明药物名称、服用剂量及疗程。
    A. 未服用任何药物及保健品
    B. 正在服用：___________，剂量：___________，疗程：___________
3. 是否有过敏史？对哪些物质过敏（如食物、药物、花粉等）？过敏时主要有哪些症状？
    A. 无过敏史
    B. 有过敏史，过敏物质：___________，过敏症状：___________
4. 曾接受过中医治疗吗？采用过哪些中医疗法（如针灸、推拿、中药汤剂等）？疗效如何？
    A. 从未接受过中医治疗
    B. 接受过，疗法：___________，疗效：___________


十八 其他补充症状
  A. 无其他补充症状
  B. 有，具体为：___________

十九 日常描述
请用几句话，如实地描述一下您的日常生活或习惯，便于大夫给出更准确、更有益于您身体健康的医嘱和建议。
    """
    data = [
        {
            "obj": {
                "title_number": "十七",
                "title": "既往病史与治疗",
                "mode": -1,
                "order": 17,
            },
            "children": [
                {
                    "obj": {
                        "title_number": "17.1",
                        "title": "您既往是否患过重大疾病？（如心脏病、中风、肝炎、肾炎等）若有，请说明疾病名称、患病时间及治疗情况。",
                        "mode": -1,
                    },
                    "children_is_clear": True,
                    "children": [
                        {
                            "obj": {
                                "title_number": "A",
                                "title": "无重大疾病史",
                                "mode": 3,
                            },
                            "children": []
                        },
                        {
                            "obj": {
                                "title_number": "B",
                                "title": "有重大疾病史",
                                "mode": -1,
                            },
                            "children": [
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "具体为: ",
                                        "mode": 2,
                                    }
                                },
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "患病时间: ",
                                        "mode": 2,
                                    },
                                },
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "治疗情况: ",
                                        "mode": 2,
                                    }
                                }
                            ]
                        },
                    ],
                },
                {
                    "obj": {
                        "title_number": "17.2",
                        "title": "目前是否正在接受其他治疗或服用药物？（包括中药、西药、保健品等）请详细说明药物名称、服用剂量及疗程。",
                        "mode": -1,
                    },
                    "children_is_clear": True,
                    "children": [
                        {
                            "obj": {
                                "title_number": "A",
                                "title": "未服用任何药物及保健品",
                                "mode": 3,
                            },
                            "children": []
                        },
                        {
                            "obj": {
                                "title_number": "B",
                                "title": "在服用",
                                "mode": -1,
                            },
                            "children": [
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "正在服用: ",
                                        "mode": 2,
                                    }
                                },
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "剂量: ",
                                        "mode": 2,
                                    },
                                },
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "疗程: ",
                                        "mode": 2,
                                    }
                                }
                            ]
                        },
                    ],
                },
                {
                    "obj": {
                        "title_number": "17.3",
                        "title": "是否有过敏史？对哪些物质过敏（如食物、药物、花粉等）？过敏时主要有哪些症状？",
                        "mode": -1,
                    },
                    "children_is_clear": True,
                    "children": [
                        {
                            "obj": {
                                "title_number": "A",
                                "title": "无过敏史",
                                "mode": 3,
                            },
                            "children": []
                        },
                        {
                            "obj": {
                                "title_number": "B",
                                "title": "有过敏史",
                                "mode": -1,
                            },
                            "children": [
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "过敏物质: ",
                                        "mode": 2,
                                    }
                                },
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "过敏症状: ",
                                        "mode": 2,
                                    },
                                }
                            ]
                        },
                    ],
                },
                {
                    "obj": {
                        "title_number": "17.4",
                        "title": "曾接受过中医治疗吗？采用过哪些中医疗法（如针灸、推拿、中药汤剂等）？疗效如何？",
                        "mode": -1,
                    },
                    "children_is_clear": True,
                    "children": [
                        {
                            "obj": {
                                "title_number": "A",
                                "title": "从未接受过中医治疗",
                                "mode": 3,
                            },
                            "children": []
                        },
                        {
                            "obj": {
                                "title_number": "B",
                                "title": "接受过",
                                "mode": -1,
                            },
                            "children": [
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "疗法: ",
                                        "mode": 2,
                                    }
                                },
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "疗效: ",
                                        "mode": 2,
                                    },
                                }
                            ]
                        },
                    ],
                }
            ],
        },
        {
            "obj": {
                "title_number": "十八",
                "title": "其他补充症状",
                "mode": -1,
                "order": 18,
            },
            "children": [
                {
                    "obj": {
                        "title_number": "18.1",
                        "title": "其他补充症状",
                        "mode": -1,
                    },
                    "children_is_clear": True,
                    "children": [
                        {
                            "obj": {
                                "title_number": "A",
                                "title": "无其他补充症状",
                                "mode": 3,
                            },
                            "children": []
                        },
                        {
                            "obj": {
                                "title_number": "B",
                                "title": "有其他补充症状",
                                "mode": -1,
                            },
                            "children": [
                                {
                                    "obj": {
                                        "title_number": "",
                                        "title": "具体为: ",
                                        "mode": 2,
                                    }
                                }
                            ]
                        },
                    ],
                }
            ],
        },
        # {
        #     "obj": {
        #         "title_number": "十九",
        #         "title": "日常描述",
        #         "mode": -1,
        #         "order": 19,
        #     },
        #     "children": [
        #         {
        #             "obj": {
        #                 "title_number": "",
        #                 "title": "请用几句话，如实地描述一下您的日常生活或习惯，便于大夫给出更准确、更有益于您身体健康的医嘱和建议。(不想输入可写无)",
        #                 "mode": -1,
        #             },
        #             "children_is_clear": True,
        #             "children": [
        #                 {
        #                     "obj": {
        #                         "title_number": "",
        #                         "title": "",
        #                         "mode": 4,
        #                     },
        #                     "children": []
        #                 }
        #             ],
        #         }
        #     ],
        # },
    ]

    def delete_old(self):
        obj = Question.objects.filter(id=648).delete()
        obj = Question.objects.filter(id=643).delete()
        # obj = Question.objects.filter(id=620).delete()

    def add_obj(self, data, parent=None, children_is_clear=False):
        result = []
        clear_ids = []
        for n, item in enumerate(data, 1):
            clear_tmp = []

            kwargs = item["obj"]
            if "order" not in kwargs:
                kwargs["order"] = n
            obj = Question.objects.create(parent=parent, **kwargs)
            clear_tmp.append(obj.id)
            result.append(obj)

            cur_result = self.add_obj(item.get("children", []), obj, item.get("children_is_clear", False))
            clear_tmp.extend([x.id for x in cur_result])
            clear_ids.append(clear_tmp)

        if children_is_clear:
            for ids in clear_ids:
                cur_clear_ids = [y for x in clear_ids for y in x if y not in ids]
                Question.objects.filter(id__in=ids).update(clear_ids=cur_clear_ids)

        return result

    def handle(self, *args, **options):
        self.delete_old()
        self.add_obj(self.data)


if __name__ == '__main__':
    Command().handle()
