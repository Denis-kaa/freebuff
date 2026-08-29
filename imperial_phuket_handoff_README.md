# Пакет передачи проекта «Клон imperial-realty-phuket.ru»

**Дата:** 2026-08-23
**Состав:** аудит сайта + смета + медиа-контент + снимок текстов

## Содержимое

| Путь | Описание |
|---|---|
| `imperial_phuket_clone_audit_estimate.md` | Технический аудит (архитектура, каталог, интерактив, внешние сервисы), смета (варианты A/B/C, без админки+бронирование), график реализации (12 нед) |
| `imperial_phuket_media_verification.md` | Отчёт о проверке целостности медиа-архива (699/699 файлов OK, SHA-256) |
| `texts/` | Снимки текстовых дампов всех 38 страниц (TXT, UTF-8; заголовки H1–H6 помечены `@@h1@@`) |
| `media/` | Медиа-архив: 699 файлов + SHA256SUMS.txt + urls.txt (92,2 МБ распаковано) |

## Быстрый старт

```bash
# 1. Распаковать весь пакет
tar -xzf imperial-phuket-handoff-20260823.tar.gz

# 2. Проверить медиа-архив (внутри пакета — media/…)
mkdir -p media_check && tar -xzf media/imperial-phuket-media-20260823.tar.gz -C media_check
cd media_check && python3 -c "
import hashlib, os
ok = 0
for line in open('SHA256SUMS.txt'):
    d, rel, size = line.split()[:2***REMOVED***
    # rel path inside SHA256SUMS is without 'media/' prefix
    ...
"
```
(либо использовать `sha256sum -c` после добавления префикса `media/` к путям)

## Структура дампов текста

`texts/NN_<раздел>_<слаг>.txt`
- `01__` — главная
- `02_zhk` — каталог ЖК; `03_…14_zhk_<проект>` — карточки (12)
- `15_districts` — районы-индекс; `16_…21_districts_<район>` — карточки районов (6)
- `22_…25_real-estate-developers-phuket*` — застройщики (индекс + 3 карточки)
- `26_blog` — блог-индекс; `27_…34_blog_<статья>` — статьи (8)
- `35_about` — о компании; `36_policy`, `37_soglasie`, `38_cookie-policy` — юр.

Формат файла: строки `TITLE:`/`DESC:` + чистый текст; заголовки помечены `@@h1@@`, `@@h2@@`, `@@h3@@` и т.д.

## Медиа (в медиа-архиве)

- 699 файлов: webp 403, jpg 201, png 64, svg 28, ico 1, jpeg 2
- Контрольные суммы: SHA256SUMS.txt (hex  путь  размер)
- Список исходных URL: urls.txt
- Сохранены пути CDN (static.tildacdn.com → media/<путь>)