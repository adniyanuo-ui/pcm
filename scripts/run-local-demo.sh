#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/pcm-master_hyd"
FRONTEND_DIR="${PROJECT_ROOT}/pcm_doctor_web"
ENV_FILE="${BACKEND_DIR}/.env.local"

if [[ ! -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
  echo "尚未初始化，请先执行 ./scripts/mac-bootstrap.sh"
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少 ${ENV_FILE}，请从 .env.example 复制并填写。"
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

cleanup() {
  if [[ -n "${BACKEND_PID:-}" ]]; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "启动 Django：http://127.0.0.1:8000"
(
  cd "${BACKEND_DIR}"
  .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
) &
BACKEND_PID=$!

sleep 1
echo "启动医生工作台：http://localhost:5174"
echo "按 Ctrl+C 同时停止前后端。"
(
  cd "${FRONTEND_DIR}"
  VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5174
)
