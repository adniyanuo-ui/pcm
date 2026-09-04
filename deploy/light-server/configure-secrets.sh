#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${PCM_DEPLOY_DIR:-/opt/pcm/app/deploy/light-server}"
ENV_FILE="${PCM_ENV_FILE:-${DEPLOY_DIR}/.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  printf '找不到配置文件：%s\n' "${ENV_FILE}" >&2
  exit 1
fi

python3 "${SCRIPT_DIR}/configure-secrets.py" "${ENV_FILE}"

cd "${DEPLOY_DIR}"
sudo docker compose up -d --force-recreate api

for attempt in $(seq 1 30); do
  status="$(sudo docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' pcm-pilot-api-1 2>/dev/null || true)"
  if [[ "${status}" == "healthy" ]]; then
    printf '%s\n' "配置已生效，后端健康检查通过。"
    exit 0
  fi
  sleep 2
done

printf '%s\n' "后端未在预期时间内恢复，请检查日志：" >&2
sudo docker compose logs --no-color --tail=80 api >&2
exit 1
