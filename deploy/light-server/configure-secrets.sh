#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="${PCM_DEPLOY_DIR:-/opt/pcm/app/deploy/light-server}"
ENV_FILE="${PCM_ENV_FILE:-${DEPLOY_DIR}/.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  printf '找不到配置文件：%s\n' "${ENV_FILE}" >&2
  exit 1
fi

python3 - "${ENV_FILE}" <<'PY'
import getpass
import os
from pathlib import Path
import sys
import tempfile


env_path = Path(sys.argv[1])
lines = env_path.read_text(encoding="utf-8").splitlines()
current = {}
for line in lines:
    if not line or line.lstrip().startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    current[key.strip()] = value.strip().strip("'\"")

prompts = (
    ("QWEN_API_KEY", "通义千问 API Key"),
    ("ALIYUN_ACCESS_KEY_ID", "阿里云 AccessKey ID"),
    ("ALIYUN_ACCESS_KEY_SECRET", "阿里云 AccessKey Secret"),
    ("ALIYUN_NLS_APPKEY", "智能语音交互项目 AppKey"),
)

updates = {}
print("输入内容不会显示；直接回车会保留原值。")
for key, label in prompts:
    state = "已配置" if current.get(key) else "未配置"
    value = getpass.getpass(f"{label}（{state}）：").strip()
    if value:
        if any(char in value for char in ("\n", "\r", "\0", "'")):
            raise SystemExit(f"{label} 含不支持的字符")
        updates[key] = value

if not updates:
    print("没有修改配置。")
    raise SystemExit(0)

seen = set()
output = []
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key = line.split("=", 1)[0].strip()
        if key in updates:
            output.append(f"{key}='{updates[key]}'")
            seen.add(key)
            continue
    output.append(line)
for key, value in updates.items():
    if key not in seen:
        output.append(f"{key}='{value}'")

fd, temp_name = tempfile.mkstemp(prefix=".env.", dir=env_path.parent, text=True)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(output) + "\n")
    os.chmod(temp_name, 0o600)
    os.replace(temp_name, env_path)
finally:
    if os.path.exists(temp_name):
        os.unlink(temp_name)
print("密钥已安全写入，配置文件权限为 600。")
PY

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
