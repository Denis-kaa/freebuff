# PARSED REQUIREMENTS

## PRIORITY MATRIX

### MUST (Blocker if missing)

| ID | Requirement | Complexity | Dependencies |
|----|-------------|------------|--------------|
| FR-001 | Авторизация по номеру телефона | Medium | — |
| FR-002 | Сохранение сессии в файл | Low | FR-001 |
| FR-003 | Автоматическое восстановление сессии | Low | FR-002 |
| FR-004 | Права доступа 600 для сессии | Low | FR-002 |
| FR-005 | Двухпанельный TUI интерфейс | High | FR-001 |
| FR-006 | Навигация по чатам | Medium | FR-005 |
| FR-007 | Отображение последних N сообщений | Medium | FR-005, FR-006 |
| FR-008 | Асинхронная загрузка сообщений | High | FR-007 |
| FR-009 | Отправка текстовых сообщений | Medium | FR-005, FR-006 |
| FR-010 | Отправка изображений | Medium | FR-009, FR-013 |
| FR-011 | Отправка видео | Medium | FR-009, FR-013 |
| FR-012 | Отправка документов | Medium | FR-009, FR-013 |
| FR-013 | Встроенный FilePicker | High | FR-005 |
| FR-014 | Горячая клавиша для FilePicker | Low | FR-013 |
| FR-015 | Обработка FloodWaitError | Medium | FR-009, FR-010, FR-011, FR-012 |
| FR-016 | Обработка сетевых ошибок | Medium | Все сетевые операции |
| FR-017 | Валидация файлов перед отправкой | Low | FR-010, FR-011, FR-012 |

**Total MUST:** 17 требований  
**Estimated Effort:** 4-5 дней

### SHOULD (Important but not blocker)

| ID | Requirement | Complexity | Dependencies |
|----|-------------|------------|--------------|
| FR-018 | Скачивание истории чата | Medium | FR-001, FR-005 |
| FR-019 | Сохранение в JSON/SQLite | Medium | FR-018 |
| FR-020 | Скачивание медиа-файлов | Medium | FR-018 |
| FR-021 | Прогресс-бар при скачивании | Low | FR-018 |
| FR-022 | Поиск по чатам и сообщениям | High | FR-005, FR-007 |
| FR-023 | Индикаторы непрочитанных | Low | FR-005 |
| FR-024 | Статус онлайн/оффлайн | Low | FR-005 |

**Total SHOULD:** 7 требований  
**Estimated Effort:** 2-3 дня

### COULD (Nice to have)

| ID | Requirement | Complexity | Dependencies |
|----|-------------|------------|--------------|
| FR-025 | Экспорт в Markdown/HTML | Low | FR-018 |
| FR-026 | Рендеринг превью картинок | High | Зависит от терминала |
| FR-027 | Поддержка тем оформления | Medium | FR-005 |

**Total COULD:** 3 требования  
**Estimated Effort:** 1-2 дня

## DEPENDENCY GRAPH

```
FR-001 (Auth)
  ↓
FR-002 (Session) → FR-003 (Restore)
  ↓                → FR-004 (Permissions)
  ↓
FR-005 (Chat List UI)
  ↓
FR-006 (Navigation) → FR-007 (Messages View)
  ↓                        ↓
FR-009 (Send Text) ← FR-008 (Async Loading)
  ↓
FR-010, FR-011, FR-012 (Send Media)
  ↓                        ↑
FR-013 (FilePicker) ← FR-014 (Hotkey)
  ↓
FR-015, FR-016, FR-017 (Error Handling)

FR-018 (Archive) → FR-019 (JSON/SQLite)
  ↓              → FR-020 (Download Media)
  ↓              → FR-021 (Progress Bar)
  ↓
FR-022 (Search)
FR-023 (Unread Indicators)
FR-024 (Online Status)

FR-025 (Export)
FR-026 (Image Preview)
FR-027 (Themes)
```

## CRITICAL PATH

```
Auth (FR-001) → Session (FR-002) → Chat List UI (FR-005) → 
Navigation (FR-006) → Messages (FR-007) → Send Text (FR-009) → 
FilePicker (FR-013) → Send Media (FR-010-012)
```

**Critical Path Duration:** 5-6 дней

## COMPLEXITY ESTIMATION (preliminary)

### By Category
- **Authentication & Session:** 4 requirements (Low-Medium)
- **TUI Interface:** 4 requirements (High)
- **Messaging:** 8 requirements (Medium-High)
- **Error Handling:** 3 requirements (Medium)
- **Archive:** 4 requirements (Medium)
- **UI Enhancements:** 3 requirements (Low-Medium)
- **Optional Features:** 3 requirements (Low-High)

### Overall Assessment
- **Total requirements:** 27
- **MUST (blockers):** 17
- **SHOULD (important):** 7
- **COULD (optional):** 3
- **Estimated complexity:** **MEDIUM (TC 5-6)**

### Risk Factors
- **TUI Complexity:** High (Textual framework, async UI)
- **Telegram API Integration:** Medium (Telethon, MTProto)
- **File Operations:** Medium (async I/O, FilePicker)
- **Cross-platform:** Medium (Linux, macOS, Windows)
- **Performance:** Medium (async, memory management)

## IMPLEMENTATION PHASES

### Phase 1: Core Foundation (Days 1-2)
- FR-001 to FR-004 (Auth & Session)
- FR-005, FR-006 (Basic TUI)

### Phase 2: Messaging (Days 3-4)
- FR-007 to FR-009 (Messages & Text)
- FR-015 to FR-017 (Error Handling)

### Phase 3: Media & FilePicker (Days 5-6)
- FR-010 to FR-014 (Media & FilePicker)

### Phase 4: Archive & Enhancements (Days 7-8)
- FR-018 to FR-024 (Archive & UI improvements)

### Phase 5: Optional Features (Days 9-10)
- FR-025 to FR-027 (Export, Preview, Themes)

## QUESTIONS & CLARIFICATIONS

### ⚠️ Требуется уточнение:
1. **FilePicker:** Встроенный (в рамках TUI) или системный диалог?
2. **N сообщений:** Какое значение N по умолчанию? (предложение: 50-100)
3. **Архивация:** Триггер — команда, горячая клавиша, или автоматическая?
4. **SQLite схема:** Какая структура таблиц для хранения сообщений?
5. **Горячие клавиши:** Полный список хоткеев (кроме Ctrl+F)?
6. **Темы оформления:** Какие темы поддерживать? (light/dark/custom)

### ✅ Принятые допущения:
- FilePicker — встроенный в TUI (навигация по файловой системе)
- N = 50 сообщений по умолчанию
- Архивация — по команде пользователя
- SQLite — простая схема (messages, chats, media)
- Темы — light/dark (системные)
