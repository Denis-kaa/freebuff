# CHECKLIST — Interior Planner (Дизайнер интерьеров)

**Версия:** 1.0  
**Дата:** 2026-08-06

## Pre-flight (запускать перед каждым билдом)

### Окружение

- [ ***REMOVED*** Node.js: `node --version` (ожидается >= 20 LTS; на Termux v26 — штатная)
- [ ***REMOVED*** Файловая система: `df -T .` (не FAT32/exFAT; если fuseblk — использовать --no-bin-links)
- [ ***REMOVED*** Symlinks: `ln -sf /dev/null /tmp/_test_ln && rm /tmp/_test_ln` (если ошибка — только web-фолбэк)
- [ ***REMOVED*** Свободная память: `free -m` (>= 1 GB available; < 512 MB — OOM risk)
- [ ***REMOVED*** Python: `python3 --version` (для http.server, если Node-сервер недоступен)

### Зависимости

- [ ***REMOVED*** `npm install --legacy-peer-deps --no-bin-links` (без ошибок)
- [ ***REMOVED*** `ls node_modules/esbuild-wasm` (бандлер установлен)
- [ ***REMOVED*** `ls node_modules/react` (React установлен)
- [ ***REMOVED*** `ls node_modules/react-native-web` (адаптер установлен)
- [ ***REMOVED*** `ls node_modules/zustand` (state manager установлен)

### Порты

- [ ***REMOVED*** `ss -tlnp | grep 8080` (порт свободен; если занят — использовать 3000)
- [ ***REMOVED*** `ss -tlnp | grep 3000` (альтернативный порт)

### Web-фолбэк

- [ ***REMOVED*** `ls node_modules/esbuild-wasm/bin/esbuild` (esbuild-wasm доступен)
- [ ***REMOVED*** Бандл собирается: `node node_modules/esbuild-wasm/bin/esbuild src/index.tsx --bundle --outfile=dist/bundle.js --alias:react-native=react-native-web --define:global=window --format=iife --loader:.tsx=tsx --platform=browser`
- [ ***REMOVED*** Бандл существует: `ls -la dist/bundle.js` (> 1 MB)
- [ ***REMOVED*** Сервер запускается: `node /tmp/serve.js </dev/null >/tmp/server.log 2>&1 &`
- [ ***REMOVED*** Сервер отвечает: `curl -s -o /dev/null -w '%{http_code***REMOVED***' http://localhost:8080/` (должен быть 200)

### Environment Doctor

```bash
cd /storage/emulated/0/PROJECTS/workstation/freebuff
python3 -m core_02.environment_doctor projects_17/interior_planner/
```

Ожидаемый результат: `ok: true` (или warnings без blockers).
