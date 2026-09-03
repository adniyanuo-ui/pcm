import re
import unicodedata
from collections.abc import Iterable


_CJK_OR_ASCII = re.compile(r"[\u3400-\u9fff]+|[a-z0-9]+", re.IGNORECASE)
_PHRASE_SEPARATOR = re.compile(r"[\s,，、;；。.!！?？:：/|]+")


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).lower().strip()


def split_phrases(value: object) -> list[str]:
    """将自由文本拆成用于解释命中的短语，保留中医复合词。"""
    text = normalize_text(value)
    if not text:
        return []
    return [part for part in _PHRASE_SEPARATOR.split(text) if part]


def unique_phrases(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        for phrase in split_phrases(value):
            if phrase not in seen:
                seen.add(phrase)
                result.append(phrase)
    return result


def search_tokens(values: Iterable[object]) -> list[str]:
    """
    将中文连续文本转换为双字索引词。

    SQLite 默认分词器不能稳定拆分“食少便溏”这类中文短语；显式生成
    “食少 / 少便 / 便溏”可在不引入额外分词依赖的情况下支持两字症状。
    """
    tokens: list[str] = []
    for value in values:
        for segment in _CJK_OR_ASCII.findall(normalize_text(value)):
            if not segment:
                continue
            if segment.isascii():
                tokens.append(segment)
            elif len(segment) == 1:
                tokens.append(segment)
            else:
                tokens.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    return tokens


def indexed_text(*values: object) -> str:
    return " ".join(search_tokens(values))


def phrase_similarity(phrase: str, text: str) -> float:
    """返回 0—1 的包含/双字覆盖率，只用于候选集重排。"""
    phrase = normalize_text(phrase)
    text = normalize_text(text)
    if not phrase or not text:
        return 0.0
    if phrase in text:
        return 1.0
    grams = set(search_tokens([phrase]))
    if not grams:
        return 0.0
    return sum(1 for gram in grams if gram in text) / len(grams)
