# AI-Dubber update v1.0.0 — изменения

Обновление собрано из ветки `feature/chunked-pipeline-gpu`.

## Основные изменения

- chunked pipeline для обработки видео;
- backpressure и планировщик задач;
- HLS progressive publish;
- метрики и profiling;
- разделение worker-процессов;
- NVENC/GPU detection и CPU fallback;
- дополнительные STT-провайдеры: AssemblyAI, Deepgram, Google STT;
- дополнительные LLM-провайдеры и registry;
- Cohere и Amazon Polly providers;
- улучшения synthesizer, transcriber и translator;
- auth и ownership checks для защищённых API endpoints;
- тесты pipeline, scheduler, backpressure, sliding window и NVENC;
- обновления Docker Compose и документации.

## Файлы зависимостей

В этом update-пакете файлы зависимостей не изменялись. Поэтому при обычном применении поверх исходной версии повторная установка `venv` и `node_modules` не требуется.

Если у заказчика есть локальные изменения в зависимостях, перед применением нужно сравнить:

- `backend/requirements.txt`;
- `frontend/package.json`;
- `frontend/package-lock.json`.

## Основа обновления

- исходная ветка проекта: `master`;
- update-ветка: `feature/chunked-pipeline-gpu`;
- последний коммит update: `416a0ba`.
