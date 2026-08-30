# AI-DUBBER — инструкция для заказчика

## 1. Что передано

Архив `ai-dubber-with-deps.tar.gz` содержит:

- исходный код AI-Dubber;
- Python-зависимости в каталоге `venv/`;
- frontend-зависимости в `frontend/node_modules/`;
- конфигурационные шаблоны и systemd-конфигурацию.

В архив **не входят**:

- `.env` и секретные ключи;
- пользовательские загрузки и результаты обработки (`uploads/`, `outputs/`);
- `.git`;
- вложенные архивы и кэши.

Размер архива: около 508 MiB.

SHA-256 для проверки после скачивания:

```text
881adabd33d58aad2dc7dc2f0c3133fa134f1b5a5b3defc061b894e31047e36d
```

Проверка:

```bash
sha256sum ai-dubber-with-deps.tar.gz
```

## 2. Требования к серверу

Рекомендуемая ОС: Ubuntu 22.04/24.04 или Debian 12.

Минимально рекомендуется:

- 4 CPU;
- 8 GB RAM;
- 30 GB свободного места;
- Python 3.12;
- Node.js 20+;
- PostgreSQL 14+;
- Redis 6+;
- FFmpeg;
- доступ к интернету для внешних API и скачивания моделей.

Для GPU-обработки дополнительно требуется NVIDIA-драйвер и CUDA, совместимые с выбранными версиями PyTorch/ONNX Runtime.

## 3. Распаковка

```bash
sudo mkdir -p /opt
sudo tar -xzf ai-dubber-with-deps.tar.gz -C /opt
sudo mv /opt/ai-dubber /opt/ai-dubber 2>/dev/null || true
cd /opt/ai-dubber
```

Если архив распаковывается в домашний каталог, можно использовать любое другое расположение, но далее нужно заменить `/opt/ai-dubber` на фактический путь.

Проверить содержимое:

```bash
cd /opt/ai-dubber
ls backend frontend docker-compose.yml
```

## 4. Создание конфигурации

Файл `.env` в архив намеренно не включён. Создайте его на основе шаблона:

```bash
cd /opt/ai-dubber
cp .env.example .env
chmod 600 .env
nano .env
```

Обязательно укажите:

- URL и пароль PostgreSQL;
- URL Redis;
- секрет приложения;
- ключи используемых AI/TTS-провайдеров;
- OAuth/Google-параметры, если используется авторизация;
- домен и CORS origins.

Нельзя передавать заказчику рабочий `.env` из исходного сервера: секреты должны быть новыми и принадлежать заказчику.

## 5. База данных и Redis

Вариант A — Docker Compose:

```bash
cd /opt/ai-dubber
docker compose up -d postgres redis
```

Вариант B — уже установленные PostgreSQL и Redis: создайте базу и пользователя PostgreSQL, запустите Redis и внесите их адреса в `.env`.

Проверка контейнеров:

```bash
docker compose ps
```

## 6. Запуск backend и workers

В архиве уже есть `venv`, поэтому обычно повторно устанавливать Python-пакеты не требуется. Если окружение не запускается из-за другой ОС или архитектуры, пересоздайте его:

```bash
cd /opt/ai-dubber
rm -rf venv
python3.12 -m venv venv
./venv/bin/pip install -r backend/requirements.txt
```

Запуск API вручную для проверки:

```bash
cd /opt/ai-dubber
./venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

В отдельном терминале запустите Celery worker согласно `DEPLOYMENT.md` и `docker-compose.yml`. Перед production-запуском обязательно прочитайте `DEPLOYMENT.md`: имена модулей и очередей должны соответствовать выбранной версии проекта.

## 7. Запуск frontend

Зависимости frontend уже вложены в архив. Для production-сборки:

```bash
cd /opt/ai-dubber/frontend
npm run build
npm run start
```

Обычно frontend слушает порт 3000, API — порт 8000.

## 8. Production через Docker Compose

Если заказчик использует Docker, предпочтительный вариант — проверить и адаптировать compose-конфигурацию:

```bash
cd /opt/ai-dubber
docker compose config
docker compose up -d --build

docker compose ps
```

Не запускайте production без проверки `.env`, доменов, volume-путей, GPU-настроек и внешних API-ключей.

## 9. Reverse proxy и HTTPS

Перед публичным доступом рекомендуется поставить Nginx или Caddy:

- HTTPS frontend: `https://example.com` → `127.0.0.1:3000`;
- API: `https://example.com/api` → `127.0.0.1:8000`.

Откройте в firewall только 80/443 и SSH. PostgreSQL, Redis и внутренние worker-порты не должны быть доступны из интернета.

## 10. Проверка после запуска

```bash
curl -f http://127.0.0.1:8000/health
curl -I http://127.0.0.1:3000

docker compose ps
journalctl -u ai-dubber-api -n 100 --no-pager
```

Затем проверьте в браузере:

1. открытие frontend;
2. регистрацию/вход;
3. загрузку короткого видео;
4. постановку задачи в очередь;
5. получение результата;
6. работу TTS/STT и нужных внешних провайдеров.

## 11. Важные ограничения

- Архив переносит зависимости, но Python-пакеты с нативными библиотеками привязаны к Linux, Python 3.12 и архитектуре сервера. На другой ОС/архитектуре `venv` лучше пересоздать.
- `frontend/node_modules` можно использовать только при совместимой версии Node.js и платформе; при проблемах выполните `npm ci`.
- Модели, API-ключи, домены и SSL-сертификаты в архив не входят.
- Не удаляйте `docker-compose.yml`, `backend/requirements.txt`, `frontend/package.json` и `.env.example`.
- Для production настройте резервное копирование PostgreSQL, `uploads/` и `outputs/`.

## 12. Краткий сценарий установки

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin ffmpeg
sudo mkdir -p /opt
sudo tar -xzf ai-dubber-with-deps.tar.gz -C /opt
cd /opt/ai-dubber
cp .env.example .env
chmod 600 .env
nano .env

docker compose config
docker compose up -d --build
docker compose ps
curl -f http://127.0.0.1:8000/health
```

Если Docker Compose в конкретной поставке не запускает backend из-за особенностей образов или GPU, используйте ручной запуск из разделов 5–7 и настройки из `DEPLOYMENT.md`.
