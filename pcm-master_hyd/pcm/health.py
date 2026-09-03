from django.db import connection
from django.http import JsonResponse

from llm_utils.rag import FormulaRetriever
from pcm import settings


def health(request):
    checks = {"database": False, "rag": False}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            checks["database"] = cursor.fetchone()[0] == 1
    except Exception:
        pass

    indexed_records = 0
    try:
        metadata = FormulaRetriever(settings.RAG_INDEX_PATH).metadata()
        indexed_records = int(metadata.get("indexed_records", 0))
        checks["rag"] = indexed_records > 0
    except Exception:
        pass

    ready = all(checks.values())
    return JsonResponse(
        {
            "status": "ok" if ready else "not_ready",
            "checks": checks,
            "rag_records": indexed_records,
        },
        status=200 if ready else 503,
    )
