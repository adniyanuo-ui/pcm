# 《中医方剂大辞典》一次性转换工具

本目录保存可复现的 OCR 与整理脚本。昂贵的 OCR 结果按页保存为 JSON，内含原始行、坐标和置信度；后续调整结构化规则时，只需重新运行 `clean_volume.py`，不需要再次 OCR。

第 1 册当前版式：

- PDF 1—10 页：封面、出版信息和凡例等单页内容；
- PDF 11—87 页：三栏方名目录；
- PDF 88 页：三栏检字页；
- PDF 89—1313 页：正文，对应书内第 1—1225 页，固定双栏。

渲染命令：

```bash
mkdir -p /tmp/dacidian_v01_pages
pdftoppm -f 1 -l 1313 -jpeg -jpegopt quality=95,optimize=y \
  -r 250 -gray 'dacidian_pdf/中医方剂大辞典（第1册）.pdf' \
  /tmp/dacidian_v01_pages/page
```

OCR 命令：

```bash
python dacidian_tools/ocr_volume.py \
  --images /tmp/dacidian_v01_pages \
  --output dacidian_text/volume_01/raw_pages \
  --start 1 --end 1313 --workers 6 --threads-per-worker 2
```

整理命令：

```bash
python dacidian_tools/clean_volume.py \
  --raw-pages dacidian_text/volume_01/raw_pages \
  --output dacidian_text/volume_01 \
  --pdf 'dacidian_pdf/中医方剂大辞典（第1册）.pdf' \
  --last-page 1313
```

自动纠错遵循“可证明、非破坏”原则：修复方号中的常见 OCR 字符、字段括号和字段名，合并视觉换行；不猜测修改药名、方名、剂量、古籍原文或异体字。所有疑似问题进入 `volume_01_needs_review.jsonl`，可随时回查原始 PDF 页。

对正文方名与目录 OCR 不一致的条目，可用 `audit_headers.py` 的 PP-OCRv6 medium 模型重新读取正文标题。只有“正文中型模型”和“独立目录 OCR”一致时才生成名称纠错映射，再将该映射传给 `clean_volume.py --name-corrections`；三方不一致的条目继续保留在复核清单中。

逐页 `raw_pages/` 不直接放入 Git。完成后用 `pack_raw_pages.py pack` 生成确定性的 `volume_XX_raw_pages.jsonl.gz`，归档会验证页码连续性并可用 `unpack` 恢复原始逐页 JSON，因此不会丢失昂贵的 OCR 中间结果。
