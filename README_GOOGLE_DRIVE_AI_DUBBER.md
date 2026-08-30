# AI-Dubber — пакет для передачи заказчику

## Состав пакета

### `ai-dubber-with-deps.tar.gz`

Основной архив проекта AI-Dubber:

- исходный код backend и frontend;
- Python-зависимости в `venv/`;
- frontend-зависимости в `frontend/node_modules/`;
- Docker Compose и deployment-конфигурации;
- документация проекта и примеры конфигурации.

Из архива исключены:

- `.env` и рабочие секреты;
- пользовательские загрузки и результаты (`uploads/`, `outputs/`);
- `.git`;
- кэши;
- вложенные архивы.

Размер: около **508 MiB**.

### `AI_DUBBER_DEPLOYMENT_INSTRUCTIONS.md`

Подробная инструкция по развёртыванию проекта на сервере заказчика:

1. требования к серверу;
2. распаковка архива;
3. настройка `.env`;
4. PostgreSQL и Redis;
5. запуск backend, workers и frontend;
6. Docker Compose;
7. HTTPS и reverse proxy;
8. проверка работоспособности.

## Проверка архива

После скачивания проверьте контрольную сумму:

```bash
sha256sum ai-dubber-with-deps.tar.gz
```

Ожидаемое значение SHA-256:

```text
881adabd33d58aad2dc7dc2f0c3133fa134f1b5a5b3defc061b894e31047e36d
```

Если значение отличается, архив скачан не полностью или был повреждён. Не распаковывайте его — скачайте заново.

Проверка целостности gzip/tar:

```bash
tar -tzf ai-dubber-with-deps.tar.gz >/dev/null && echo "Archive OK"
```

## Быстрый старт для заказчика

```bash
sudo mkdir -p /opt
sudo tar -xzf ai-dubber-with-deps.tar.gz -C /opt
cd /opt/ai-dubber
cp .env.example .env
chmod 600 .env
nano .env
```

После заполнения `.env` продолжайте по инструкции `AI_DUBBER_DEPLOYMENT_INSTRUCTIONS.md`.

## Требования

Рекомендуемый сервер:

- Ubuntu 22.04/24.04 или Debian 12;
- 4 CPU;
- 8 GB RAM;
- 30 GB свободного места;
- Python 3.12;
- Node.js 20+;
- PostgreSQL 14+;
- Redis 6+;
- FFmpeg.

Для GPU-функций нужны совместимые NVIDIA-драйверы и CUDA.

## Важно

- Рабочий `.env` не передаётся: заказчик должен создать собственные секреты и API-ключи.
- Встроенные `venv` и `node_modules` рассчитаны на Linux x86_64, Python 3.12 и совместимую версию Node.js.
- На другой ОС или архитектуре зависимости необходимо пересоздать.
- Перед публичным запуском настройте HTTPS, firewall и резервное копирование базы данных, загрузок и результатов.
