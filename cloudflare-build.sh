#!/usr/bin/env bash
# Cloudflare Workers Builds（Linux）建置／部署入口。
# 若快取工作目錄殘留 requirements.txt，pywrangler 會拒絕建置；先刪再部署。
# 用法（儀表板 Deploy command）：
#   生產： bash cloudflare-build.sh
#   預覽： bash cloudflare-build.sh --env preview
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
rm -f requirements.txt
exec uvx --from workers-py pywrangler deploy "$@"
