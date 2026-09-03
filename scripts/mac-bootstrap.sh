#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/pcm-master_hyd"
FRONTEND_DIR="${PROJECT_ROOT}/pcm_doctor_web"

for command_name in python3 node npm; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "缺少 ${command_name}，请先安装后重新运行。"
    exit 1
  fi
done

echo "1/5 创建 Python 虚拟环境"
python3 -m venv "${BACKEND_DIR}/.venv"

echo "2/5 安装后端依赖"
PIP_DISABLE_PIP_VERSION_CHECK=1 "${BACKEND_DIR}/.venv/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

echo "3/5 初始化本地数据库"
"${BACKEND_DIR}/.venv/bin/python" "${BACKEND_DIR}/manage.py" migrate

echo "4/5 构建方剂检索索引"
if [[ ! -f "${BACKEND_DIR}/var/rag/fangji.sqlite3" ]]; then
  (
    cd "${BACKEND_DIR}"
    .venv/bin/python -m llm_utils.rag build
  )
else
  echo "索引已经存在，跳过重复构建。"
fi

echo "5/5 安装医生工作台依赖"
(
  cd "${FRONTEND_DIR}"
  npm ci
)

if [[ ! -f "${BACKEND_DIR}/.env.local" ]]; then
  cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env.local"
  echo "已生成 ${BACKEND_DIR}/.env.local，请填写大模型和语音服务密钥。"
fi

if [[ ! -f "${FRONTEND_DIR}/.env.local" ]]; then
  cp "${FRONTEND_DIR}/.env.example" "${FRONTEND_DIR}/.env.local"
fi

echo
echo "初始化完成。下一步："
echo "1. 编辑 pcm-master_hyd/.env.local"
echo "2. 创建医生账号：cd pcm-master_hyd && .venv/bin/python manage.py createsuperuser"
echo "3. 启动演示：./scripts/run-local-demo.sh"
