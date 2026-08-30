# AI-Dubber — update package v1.0.0

Этот пакет предназначен для наложения обновлений на исходный архив AI-Dubber, который заказчик ранее передал исполнителю через Google Drive.

## Файлы пакета

- `ai-dubber-update-v1.0.0.tar.gz` — только код и документация обновления;
- `AI_DUBBER_UPDATE_v1.0.0_README.md` — эта инструкция;
- `AI_DUBBER_CHANGELOG_v1.0.0.md` — список изменений.

Размер update-архива: около **4.2 MiB**.

В update-архив **не входят**:

- `venv/` и `frontend/node_modules/`;
- `.env`;
- `.git`;
- `uploads/` и `outputs/`;
- вложенные архивы;
- база данных и пользовательские данные.

## Проверка архива

```bash
sha256sum ai-dubber-update-v1.0.0.tar.gz
```

Ожидаемая SHA-256 сумма:

```text
da87bc2b108e20bbb36675d5d7a5eff6f533575e8f70aae10b73c10230694ad7
```

Проверка структуры:

```bash
tar -tzf ai-dubber-update-v1.0.0.tar.gz >/dev/null && echo "Archive OK"
```

## Важное условие

Update рассчитан на исходную версию AI-Dubber, от которой была создана ветка обновления. Перед применением сохраните резервную копию текущей установки.

Не применяйте update поверх другого продукта или сильно изменённой версии без предварительного сравнения.

## Безопасное применение на сервере

Предположим, текущий проект находится в `/opt/ai-dubber`.

### 1. Загрузить файлы на сервер

Загрузите `ai-dubber-update-v1.0.0.tar.gz` и этот README на сервер любым безопасным способом.

### 2. Создать резервную копию

```bash
sudo tar -czf \
  /opt/ai-dubber-backup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz \
  --exclude='ai-dubber/venv' \
  --exclude='ai-dubber/frontend/node_modules' \
  --exclude='ai-dubber/.git' \
  /opt/ai-dubber
```

Если в проекте много пользовательских результатов, отдельно скопируйте `uploads/`, `outputs/` и базу данных в резервное хранилище.

### 3. Распаковать update во временный каталог

```bash
rm -rf /tmp/ai-dubber-update
mkdir -p /tmp/ai-dubber-update
tar -xzf ai-dubber-update-v1.0.0.tar.gz -C /tmp/ai-dubber-update
```

### 4. Наложить только код

Команда не затрагивает `.env`, виртуальное окружение, frontend-зависимости и пользовательские данные:

```bash
sudo rsync -a \
  --exclude='.env' \
  --exclude='venv/' \
  --exclude='frontend/node_modules/' \
  --exclude='uploads/' \
  --exclude='outputs/' \
  --exclude='.git/' \
  /tmp/ai-dubber-update/ai-dubber/ \
  /opt/ai-dubber/
```

### 5. Обновить зависимости, если потребуется

В этой версии update-файлы зависимостей не менялись. Если заказчик самостоятельно менял `requirements.txt` или `package.json`, сравните их перед установкой.

При необходимости:

```bash
cd /opt/ai-dubber
./venv/bin/pip install -r backend/requirements.txt
cd frontend
npm ci
```

### 6. Проверить и перезапустить сервисы

```bash
cd /opt/ai-dubber
./venv/bin/python -m compileall -q backend
./venv/bin/pytest backend/tests -q
```

Перезапуск systemd-сервисов:

```bash
sudo systemctl restart ai-dubber-api
sudo systemctl restart ai-dubber-worker
sudo systemctl restart ai-dubber-frontend
```

Проверка:

```bash
curl -f http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3000
sudo systemctl --no-pager --full status \
  ai-dubber-api ai-dubber-worker ai-dubber-frontend
```

## Откат

Если после обновления возникла проблема, остановите сервисы и восстановите каталог из созданного backup-архива. Перед восстановлением обязательно сохраните текущие `.env`, `uploads/`, `outputs/` и базу данных.

## Что изменилось

Подробный список находится в `AI_DUBBER_CHANGELOG_v1.0.0.md`.
