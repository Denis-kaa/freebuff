#!/bin/bash
# Одноразовый деплой «Северный чай» AI-консультант на сервер wimp
# Запуск: bash deploy_severny_chay.sh
set -euo pipefail

KEY="[REDACTED_GEMINI_KEY]"
SRC="./projects_17/severny_chay/main.py"
DST_DIR="~/ai_consultant"

echo "=== Шаг 1: mkdir ==="
ssh wimp "mkdir -p $DST_DIR"

echo "=== Шаг 2: scp main.py ==="
scp "$SRC" "wimp:$DST_DIR/"

echo "=== Шаг 3: venv + pip install ==="
ssh wimp "cd $DST_DIR && python3 -m venv venv && ./venv/bin/pip install -q fastapi uvicorn pydantic google-genai"

echo "=== Шаг 4: создаю systemd-сервис ==="
ssh wimp "sudo tee /etc/systemd/system/ai-consultant.service <<'UNIT'
[Unit***REMOVED***
Description=AI Consultant FastAPI — Северный чай
After=network.target

[Service***REMOVED***
User=root
WorkingDirectory=/root/ai_consultant
Environment=\"GEMINI_API_KEY=$KEY\"
ExecStart=/root/ai_consultant/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install***REMOVED***
WantedBy=multi-user.target
UNIT"

echo "=== Шаг 5: daemon-reload + enable + start ==="
ssh wimp "sudo systemctl daemon-reload && sudo systemctl enable ai-consultant && sudo systemctl start ai-consultant"

echo "=== Шаг 6: статус ==="
ssh wimp "sudo systemctl status ai-consultant --no-pager"

echo "=== Шаг 7: проверка HTTP ==="
ssh wimp "sleep 2 && curl -s -o /dev/null -w 'HTTP %{http_code***REMOVED***\n' http://127.0.0.1:8000/"