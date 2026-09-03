# 《中医方剂大辞典》正编合并语料

本目录由 `dacidian_tools/merge_corpus.py` 从第 1—10 册确定性生成。

- `fangji_entries.jsonl`：方号 `00001—96592` 的全部 96592 条记录；
- `rag_exclusions.jsonl`：因源 PDF 全白页或正文部分缺失而禁止进入 RAG 的 211 条记录；
- `review_index.jsonl`：各册质量标记的合并索引，可按卷号和 PDF 页回查；
- `unresolved_header_audit.jsonl`：正文、目录和中型 OCR 尚未达成一致的方名疑点；
- `quality_summary.json`：全书统计、空白页清单及输出 SHA-256。

构建 RAG 时，必须排除 `record_status` 不为 `complete` 的记录。当前可入库 96381 条，排除 211 条。未经复核不得用目录或模型猜测补写缺页正文。
