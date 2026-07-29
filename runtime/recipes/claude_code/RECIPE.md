# RECIPE: Claude Code

> **Runtime:** Claude Code (Anthropic)
> **Уровень:** 2 — Запускается вручную
> **Платформа:** Linux/macOS (Android/Termux — экспериментально)
> **Проверено:** 2026-07-29 (только stdio)

---

## 1. Установка

### Требования
- Node.js >= 18
- npm
- proot (для Android/Termux)
- API ключ Anthropic

### Linux/macOS
```bash
npm install -g @anthropic/claude-code
```

### Android/Termux (экспериментально)
```bash
# 1. Установить proot + glibc
pkg install proot proot-distro
proot-distro install debian

# 2. Войти в proot
proot-distro login debian

# 3. Установить Node.js и Claude Code
apt update && apt install nodejs npm -y
npm install -g @anthropic/claude-code

# 4. Настроить API ключ
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Проверка
```bash
claude --version
claude --help
```

---

## 2. Зависимости

### Системные
```
node >= 18, npm, git
proot + proot-distro (Android)
glibc (Android)
```

### npm
```
@anthropic/claude-code (latest)
```

---

## 3. Wrapper

### Для Android/Termux (proot)
```bash
#!/data/data/com.termux/files/usr/bin/bash
# ~/.local/bin/claude-wrapper
# Запускает Claude Code внутри proot

exec proot-distro login debian -- bash -c "
    export ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY'
    exec claude"
```

Использование:
```bash
chmod +x ~/.local/bin/claude-wrapper
claude-wrapper --help
```

---

## 4. Patch

### Известные проблемы Android

1. **libc incompatibility**: Claude Code скомпилирован под glibc, Termux использует bionic libc.
   **Решение**: proot-distro debian.

2. **RAM ограничения**: Claude Code требует ~2 GB RAM.
   **Решение**: закрыть фоновые приложения, использовать OOM Protection.

3. **npm global bin not in PATH**:
   ```bash
   export PATH="$(npm root -g)/../bin:$PATH"
   ```

---

## 5. Обновление

```bash
npm update -g @anthropic/claude-code
```

В proot:
```bash
proot-distro login debian -- npm update -g @anthropic/claude-code
```

---

## 6. Удаление

```bash
npm uninstall -g @anthropic/claude-code
```

В proot:
```bash
proot-distro login debian -- npm uninstall -g @anthropic/claude-code
```

---

## 7. Doctor

```bash
python scripts/doctor.py --check-runtime claude-code
```

Проверяет:
- Node.js версию (`node --version`)
- npm доступность (`npm --version`)
- Наличие бинарника Claude (`which claude`)
- proot (Android: `proot-distro list`)
- API ключ (`$ANTHROPIC_API_KEY`)
- MCP соединение (`python scripts/mcp_server.py` + bridge_connect)

---

## 8. Recovery

```bash
# 1. Переустановка npm глобально
npm uninstall -g @anthropic/claude-code && npm install -g @anthropic/claude-code

# 2. Очистка npm кэша
npm cache clean --force

# 3. Переустановка proot (Android)
proot-distro remove debian
proot-distro install debian

# 4. Проверка API ключа
echo $ANTHROPIC_API_KEY | head -c 10
```

---

## Ограничения

- ❌ Не работает нативно в Termux (требует proot)
- ❌ Высокое потребление RAM (~2 GB)
- ⚠️ Только stdio транспорт (MCP)
- ⚠️ Не тестировался на Android в production

---

## Связанные документы

- [COMPATIBILITY_MATRIX.md***REMOVED***(../../../docs/core/COMPATIBILITY_MATRIX.md)
- [FreeBuff RECIPE.md***REMOVED***(../freebuff/RECIPE.md)
- [BRIDGE_PLATFORM_SPECIFICATION.md***REMOVED***(../../../docs/plugin/BRIDGE_PLATFORM_SPECIFICATION.md)
