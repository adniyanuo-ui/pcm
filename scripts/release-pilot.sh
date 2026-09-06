#!/usr/bin/env bash
# Run only after the user has reviewed this exact commit in the development environment.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ "${1:-}" != "--approved-commit" || -z "${2:-}" ]]; then
  echo '用法：bash scripts/release-pilot.sh --approved-commit <用户整体验收通过的完整提交SHA>' >&2
  exit 2
fi
approved_commit="$2"
current_commit="$(git rev-parse HEAD)"
[[ "$(git branch --show-current)" == develop ]] || { echo '必须在 develop 分支运行' >&2; exit 1; }
[[ "$approved_commit" == "$current_commit" ]] || { echo '当前代码与验收提交不一致，请重新验收' >&2; exit 1; }
[[ -z "$(git status --porcelain)" ]] || { echo '工作区尚有未提交修改，停止发布' >&2; exit 1; }

PCM_ENV=test ./pcm-master_hyd/.venv/bin/python pcm-master_hyd/manage.py test llm user speech pcm llm_utils.rag.tests
PCM_ENV=test ./pcm-master_hyd/.venv/bin/python pcm-master_hyd/manage.py makemigrations --check --dry-run
npm --prefix pcm_doctor_web test
npm --prefix pcm_doctor_web run build
git diff --check
[[ "$(git rev-parse HEAD)" == "$approved_commit" && -z "$(git status --porcelain)" ]] || { echo '检查期间代码发生变化，停止发布' >&2; exit 1; }
git fetch origin main develop
git merge-base --is-ancestor origin/main HEAD || { echo '生产分支有未整合的更新，停止发布' >&2; exit 1; }
git merge-base --is-ancestor origin/develop HEAD || { echo '开发分支有未整合的更新，停止发布' >&2; exit 1; }
# No force push: either both refs advance together or neither does.
git push --atomic origin HEAD:develop HEAD:main
echo "已推送验收版本 $approved_commit，香港自动部署将开始。"
echo '这只确认推送成功；仍须核对香港实际部署版本、健康检查及虚构病例冒烟测试，再通知医生试用。'
