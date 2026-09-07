#!/bin/sh
set -eu

echo "创建SQLite迁移前备份"
python manage.py backup_sqlite_database --keep 7

echo "应用数据库迁移"
python manage.py migrate --noinput

if [ ! -f "${PCM_RAG_INDEX_PATH}" ]; then
  echo "首次构建方剂RAG索引"
  python -m llm_utils.rag build \
    --corpus "${PCM_RAG_CORPUS_PATH}" \
    --syndrome-index "${PCM_RAG_SYNDROME_INDEX_PATH}" \
    --output "${PCM_RAG_INDEX_PATH}"
fi

echo "启动Gunicorn"
exec gunicorn pcm.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-1}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --timeout "${GUNICORN_TIMEOUT:-180}" \
  --access-logfile - \
  --error-logfile -
