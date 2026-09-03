# 方剂大辞典本地检索层

该模块为临床工作台提供候选基础方检索，不直接输出诊断或最终处方。

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

返回结果含方号、原文字段、正文册/PDF页/书内页、命中理由和附编病证索引证据。
evidence_coverage 与 retrieval_score 只用于候选排序，不代表临床有效率。
