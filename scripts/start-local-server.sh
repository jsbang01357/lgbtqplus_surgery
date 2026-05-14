#!/bin/zsh
set -eu

cd /Users/jsbang/Developer/00_Jisong_Cloud/01_jisong_cloud

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if ! docker info >/dev/null 2>&1; then
  open -gj -a Docker || true
fi

for _ in {1..60}; do
  if docker info >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

docker compose --env-file .env.local -f docker-compose.local.yml up -d
