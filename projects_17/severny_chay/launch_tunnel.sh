#!/bin/bash
# Лаунчер: поднимает uvicorn, затем cloudflared-туннель.
# URL сохраняется в /tmp/severny_chay_url.txt
set -euo pipefail

cd /mnt/sdcard/PROJECTS/workstation/freebuff/projects_17/severny_chay

export GEMINI_API_KEY="${GEMINI_API_KEY:?set GEMINI_API_KEY in environment}"

# Стартуем uvicorn в фоне
python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
UVICORN_PID=$!

# Ждём готовности
for i in $(seq 1 20); do
  sleep 1
  if curl -s -o /dev/null http://127.0.0.1:8000/ 2>/dev/null; then
    echo "uvicorn OK (PID $UVICORN_PID)"
    break
  fi
  if [ "$i" -eq 20 ***REMOVED***; then
    echo "uvicorn не стартовал"; exit 1
  fi
done

# Запускаем cloudflared и ловим trycloudflare.com URL
cloudflared tunnel --url http://127.0.0.1:8000 2>&1 | while IFS= read -r line; do
  echo "$line"
  # Ищем строку с trycloudflare.com
  if echo "$line" | grep -qoP 'https://[a-zA-Z0-9.-***REMOVED***+\.trycloudflare\.com'; then
    URL=$(echo "$line" | grep -oP 'https://[a-zA-Z0-9.-***REMOVED***+\.trycloudflare\.com')
    echo "PUBLIC_URL=$URL" > /tmp/severny_chay_url.txt
    echo "=== ГОТОВО: $URL ==="
  fi
done

# Если cloudflared упал — убиваем uvicorn
kill $UVICORN_PID 2>/dev/null || true