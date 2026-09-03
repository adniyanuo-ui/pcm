"""《中医方剂大辞典》本地检索层。

该包只负责可追溯的候选方召回与排序，不产生诊断或处方结论。
"""

from .index import FormulaIndexBuilder
from .retriever import FormulaRetriever, RetrievalQuery

__all__ = ["FormulaIndexBuilder", "FormulaRetriever", "RetrievalQuery"]
