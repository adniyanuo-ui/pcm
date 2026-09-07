# 分层方剂检索

该模块为临床工作台提供候选基础方检索，不直接输出诊断或最终处方。当前默认单一路径为：

~~~text
已确认病机与治法
  → 62 个治疗结构原型/方族
  → 300 首 Gold 核心候选方
  → 组成、方义原文、实际功用、实际主治反向核验
  → 核心证据不足或方向冲突时，回退 96,381 条历史全库
~~~

数千首高质量经典方中间层尚未建设，不在返回结果中伪装为已完成。现有全库
FTS5/病证索引完整保留，但在医生坐诊流程中只承担长尾兜底。
若病性与已确认治法本身寒热方向相反，检索会在治疗原型层停止并要求医师修订，
不会用全库搜索掩盖上游矛盾。

## 构建索引

在后端目录执行：

~~~bash
cd pcm-master_hyd
python -m llm_utils.rag build
~~~

索引已经存在时不会默认覆盖；确认需要重建后执行：

~~~bash
python -m llm_utils.rag build --force
~~~

默认读取以下两个文件：

- ../dacidian_text/corpus/fangji_entries.jsonl
- ../dacidian_text/volume_11/volume_11_syndrome_index.jsonl

默认生成 var/rag/fangji.sqlite3。该文件是可重复生成的本地索引，不进入 Git。

构建过程只写临时文件，全部完成后再原子替换正式索引；所有 record_status 不为
complete 的记录均被排除。

## 构建核心方清单

全库索引构建完成后执行：

~~~bash
python manage.py build_gold_formula_set --size 300
~~~

清单生成在 `llm_utils/rag/gold_formulas.jsonl`，仅保存辞典条目 ID、治疗原型标签和
归类依据；组成、功用、主治等事实运行时仍按 ID 从辞典索引读取。首期门禁要求方源、
组成、功用、主治、册数、PDF 页码和书内页码完整。同名方有已知出处时必须同时匹配
出处，否则宁可不进入 Gold。构建时先收入官方目录候选和方族代表方，再确保原型覆盖，
其余名额按辞典已有方剂学/规范引用及方论证据排序。自动归类统一标为待临床复核，
不等同于专家审定，也不把“资料完整”表述为专家确认的黄金标准。

## 命令行验证

~~~bash
python -m llm_utils.rag search \
  --symptom 乏力 --symptom 食少 --symptom 便溏 \
  --mechanism 脾胃气虚 --treatment 益气健脾 --top-k 5
~~~

查看索引状态：

~~~bash
python -m llm_utils.rag status
~~~

## API

CMS 登录后调用：

~~~http
POST /api/cms/llm/rag/search/
Content-Type: application/json
~~~

~~~json
{
  "symptoms": ["乏力", "食少", "便溏"],
  "tongue": ["舌淡", "苔薄白"],
  "pulse": ["脉细弱"],
  "mechanisms": ["脾胃气虚", "运化失健"],
  "syndromes": ["脾胃气虚证"],
  "treatments": ["益气健脾"],
  "top_k": 5
}
~~~

返回结果含治疗原型、检索停止层、方号、原文字段、正文册/PDF页/书内页、命中理由、
附编病证索引证据和反向核验。反向核验读取辞典组成、功用、主治及可用方论；辞典没有
独立方论时明确留空，不由模型补写。核验结论为“不足”的条目直接淘汰；如果核心方和
历史全库都没有通过门禁的候选方，则不提供可带入处方的结果，并要求补充四诊或修订治法。
evidence_coverage 与 retrieval_score 只用于候选排序，不代表临床有效率。
