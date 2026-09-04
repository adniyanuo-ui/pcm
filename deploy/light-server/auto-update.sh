#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${PCM_APP_ROOT:-/opt/pcm/app}"
DEPLOY_DIR="${APP_ROOT}/deploy/light-server"
STATE_DIR="${PCM_STATE_DIR:-/opt/pcm/state}"
STATE_FILE="${STATE_DIR}/deployed_commit"
LOCK_FILE="${STATE_DIR}/auto-update.lock"

mkdir -p "${STATE_DIR}"
exec 9>"${LOCK_FILE}"
flock -n 9 || exit 0

cd "${APP_ROOT}"
git fetch --quiet origin main
REMOTE_COMMIT="$(git rev-parse origin/main)"
DEPLOYED_COMMIT="$(cat "${STATE_FILE}" 2>/dev/null || true)"

if [[ "${REMOTE_COMMIT}" == "${DEPLOYED_COMMIT}" ]]; then
  exit 0
fi

git merge --ff-only origin/main
cd "${DEPLOY_DIR}"
docker compose build
docker compose up -d

for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error --max-time 5 \
    "https://${PCM_DOMAIN}/api/health/" >/dev/null; then
    printf '%s\n' "${REMOTE_COMMIT}" > "${STATE_FILE}"
    logger -t pcm-auto-update "deployed ${REMOTE_COMMIT}"
    exit 0
  fi
  sleep 2
done

logger -t pcm-auto-update "health check failed for ${REMOTE_COMMIT}"
exit 1
