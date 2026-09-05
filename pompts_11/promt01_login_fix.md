# Задача: Отладка логина GapirAI.uz

## Контекст

GapirAI.uz — видео-дубляж на Next.js (frontend :3000) + FastAPI (backend :8000). nginx reverse proxy на :80.

**Путь к проекту:** `/opt/ai-dubber`

**Сегодня были изменения:**
1. `backend/api/auth_routes.py` — login для verified пользователей теперь возвращает JWT напрямую (без email-кода)
2. `frontend/lib/auth.ts` — apiLogin возвращает `AuthResult | PendingVerification`
3. `frontend/hooks/useAuth.ts` — login() проверяет: verified → сохраняет token → redirect
4. `frontend/app/login/page.tsx` — handleSubmit обрабатывает оба сценария
5. `frontend/app/auth/callback/page.tsx` — новая страница
6. `backend/services/plans.py` — бесплатный план: free_minutes=5.0

**Проблема:** Пользователь `den4ikorm@gmail.com` (is_verified=true) при входе видит бесконечный спиннер — ничего не происходит.

## Что сделать

### Шаг 1: Диагностика

```bash
# Проверить логи backend
journalctl -u ai-dubber-api --no-pager -n 50

# Проверить что login endpoint отвечает
curl -sS http://127.0.0.1:8000/auth/login -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"den4ikorm@gmail.com","password":"demo123"}'

# Проверить что отвечает через nginx (not localhost:8000)
curl -sS http://127.0.0.1/auth/login -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"den4ikorm@gmail.com","password":"demo123"}'

# Проверить/demo аккаунт
curl -sS http://127.0.0.1:8000/auth/login -X POST \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@gapirai.uz","password":"demo123"}'
```

### Шаг 2: Проверить пароль

Пароль `den4ikorm@gmail.com` неизвестен. Сбросить через PostgreSQL:

```bash
cd /opt/ai-dubber
venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
from backend.services.auth import hash_password
from sqlalchemy import create_engine, text
pw = hash_password('demo123')
engine = create_engine('postgresql://dubber:dubber123@localhost:5432/dubber_db')
with engine.begin() as conn:
    conn.execute(text(\"UPDATE users SET password_hash = :p WHERE email = 'den4ikorm@gmail.com'\"), {'p': pw})
print('Password reset to demo123 for den4ikorm@gmail.com')
"
```

### Шаг 3: Проверить фронтенд

```bash
# Проверить что /auth/callback доступен
curl -sS -o /dev/null -w '%{http_code}' 'http://127.0.0.1/auth/callback?token=test'

# Проверить что login page рендерится
curl -sS -o /dev/null -w '%{http_code}' 'http://127.0.0.1/login'

# Проверить что JS-бандл содержит новую логику
grep -c 'access_token' /opt/ai-dubber/frontend/.next/standalone/.next/static/chunks/app/login/page-*.js 2>/dev/null
```

### Шаг 4: E2E тест через playwright (если установлен)

```bash
cd /opt/ai-dubber
venv/bin/python3 -c "
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 1. Открыть login
    page.goto('http://127.0.0.1/login')
    page.wait_for_load_state('networkidle')
    print('Login page loaded:', page.title())
    
    # 2. Заполнить форму
    page.fill('input[type=\"email\"]', 'demo@gapirai.uz')
    page.fill('input[type=\"password\"]', 'demo123')
    page.click('button[type=\"submit\"]')
    
    # 3. Ждём редирект на dashboard (или ошибку)
    time.sleep(3)
    print('Current URL:', page.url)
    print('Page content (first 500):', page.content()[:500])
    
    browser.close()
"
```

### Шаг 5: Если проблема в CORS/cookie

Проверить что `auth_token` cookie устанавливается корректно. Если фронтенд не отправляет credentials:

```bash
# Проверить CORS headers
curl -sS -D - http://127.0.0.1:3000 -H 'Origin: http://185.233.184.192' 2>&1 | grep -i 'access-control\|set-cookie'
```

## Ожидаемый результат

1. Login `demo@gapirai.uz` / `demo123` → JWT напрямую (без email-кода)
2. Login `den4ikorm@gmail.com` / `demo123` → JWT напрямую (после сброса пароля)
3. Frontend: спиннер исчезает, редирект на dashboard

## Сервисы

```bash
systemctl status ai-dubber-api ai-dubber-frontend ai-dubber-worker
```

## Если что-то не работает

Покажи:
1. Вывод `journalctl -u ai-dubber-api --no-pager -n 30`
2. Результат curl к `/auth/login`
3. Текущий код `auth_routes.py` (строки 148-170)
