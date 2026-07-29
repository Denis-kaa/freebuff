# RECIPE: FreeBuff CLI

> **Runtime:** FreeBuff CLI
> **Уровень:** 4 — Stable
> **Платформа:** Android/Termux, Linux, macOS
> **Проверено:** 2026-07-29 (1143 теста, 0 failures)

---

## 1. Установка

### Способ 1: pip (рекомендуемый)

```bash
pip install freebuff
```

Проверка:
```bash
freebuff --version
which freebuff
# ~/.local/bin/freebuff
```

### Способ 2: из исходников

```bash
cd /path/to/freebuff
pip install -e .
```

---

## 2. Зависимости

### Системные (Termux)
```bash
pkg install python git curl wget
```

### Python
```
python >= 3.11
```
Из `requirements.txt`:
```
httpx, pyyaml, fastapi, uvicorn, python-telegram-bot
```

---

## 3. Wrapper

FreeBuff CLI не требует wrapper'а. Запускается напрямую:

```bash
freebuff                    # Интерактивный режим
freebuff --task "задача"    # Одноразовый запуск
```

---

## 4. Patch

### Termux-specific
```bash
# Если FreeBuff не находит .local/bin
export PATH="$HOME/.local/bin:$PATH"
# Добавить в .bashrc:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### OOM Protection
FreeBuff CLI автоматически запускает OOM Protection перед стартом.
См. `scripts/oom_protect.sh`.

---

## 5. Обновление

```bash
pip install --upgrade freebuff
```

После обновления:
```bash
freebuff --version   # Проверить версию
python -m pytest tests/ -q   # Прогнать тесты
```

---

## 6. Удаление

```bash
pip uninstall freebuff -y
```

Остаточные файлы:
```bash
rm -rf ~/.local/bin/freebuff
rm -rf ~/.freebuff/
```

---

## 7. Doctor

```bash
python scripts/doctor.py --check-runtime freebuff
```

Проверяет:
- Наличие бинарника (`which freebuff`)
- Версию (`freebuff --version`)
- Возможность запуска (`freebuff --help`)
- OOM Protection (`scripts/oom_protect.sh`)
- Тесты (`pytest tests/ -q`)

---

## 8. Recovery

Если FreeBuff CLI перестал работать:

```bash
# 1. Переустановка
pip uninstall freebuff -y && pip install freebuff

# 2. Проверка зависимостей
pip install -r requirements.txt

# 3. Очистка кэша
rm -rf ~/.freebuff/cache/

# 4. Диагностика
python scripts/doctor.py --full
```

---

## Связанные документы

- [COMPATIBILITY_MATRIX.md***REMOVED***(../../../docs/core/COMPATIBILITY_MATRIX.md)
- [RUNTIME_VALIDATION_FRAMEWORK.md***REMOVED***(../../../docs/core/RUNTIME_VALIDATION_FRAMEWORK.md)
- [BUFFY.md***REMOVED***(../../../BUFFY.md)
