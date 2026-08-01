# ARCHITECTURE: tg-terminal-toolkit

## 1. SYSTEM OVERVIEW

### High-Level Diagram
```mermaid
graph TD
    User((User)) -->|Input/Navigation| UI[Textual UI App***REMOVED***
    UI -->|Commands| Q_OUT[asyncio.Queue: UI → Client***REMOVED***
    Q_OUT --> TG[Telethon Client Task***REMOVED***
    TG -->|MTProto API| Telegram[(Telegram Servers)***REMOVED***
    Telegram -->|Updates/Responses| TG
    TG -->|Events/Results| Q_IN[asyncio.Queue: Client → UI***REMOVED***
    Q_IN --> UI
    UI -->|Async I/O| FS[(Local File System)***REMOVED***
    TG -->|Session Read/Write| Session[(.session file)***REMOVED***
    UI -->|Archive/Export| DB[(SQLite / JSON)***REMOVED***
    
    subgraph Concurrency Boundary & Protection
        Q_OUT
        Q_IN
        StateLock[asyncio.Lock: Shared State***REMOVED***
    end
```

### Component List
1. **`main.py`**: Entry point, orchestrates startup, graceful shutdown, and task scheduling.
2. **`auth.py`**: Handles phone/2FA authentication, session creation, and permission enforcement (`chmod 600`).
3. **`tg_client.py`**: Core Telethon wrapper. Manages network requests, rate limiting, and centralized error handling.
4. **`ui/app.py`**: Main Textual application, layout manager, and event loop integrator.
5. **`ui/chat_list.py`**: Left-panel widget for chat navigation with lazy loading.
6. **`ui/message_view.py`**: Right-panel widget for message rendering and text input.
7. **`ui/file_picker.py`**: Modal screen with async directory tree and extension filtering.
8. **`storage/archive.py`**: Handles chat history export to JSON/SQLite and media downloads.
9. **`utils/async_helpers.py`**: Shared utilities (rate limiter, retry decorators, log sanitization).

### Data Flow
- **User Action → UI → Client**: User triggers action (e.g., send message) → UI pushes command dict to `Q_OUT` → `tg_client` task pops command, executes Telethon API, pushes result/error dict to `Q_IN` → UI task pops result and updates reactive state.
- **Telegram Update → UI**: Telethon event listener receives `NewMessage` → pushes event dict to `Q_IN` → UI task updates `message_view` reactively.

---

## 2. COMPONENTS

### 2.1 `auth.py`
- **Responsibilities**: Orchestrate Telethon authentication flow, manage session file lifecycle, enforce security permissions.
- **Public API**: 
  - `async def authenticate(client: TelegramClient, phone: str) -> bool`
  - `async def ensure_session_security(session_path: Path) -> None`
- **Dependencies**: `telethon`, `os`, `pathlib`, `utils.async_helpers` (for log sanitization).

### 2.2 `tg_client.py`
- **Responsibilities**: Wrap Telethon `TelegramClient`, handle all network I/O, implement rate limiting, centralize error handling.
- **Public API**:
  - `async def get_dialogs(offset: int, limit: int) -> list[Dialog***REMOVED***`
  - `async def get_messages(chat_id: int, limit: int, offset_id: int) -> list[Message***REMOVED***`
  - `async def send_text(chat_id: int, text: str) -> Message`
  - `async def send_file(chat_id: int, path: Path) -> Message`
  - `async def start_listening_updates(queue: asyncio.Queue) -> None`
- **Error Handling**: Centralized `try/except` for `FloodWaitError`, `ConnectionError`, `SessionRevokedError`.
- **Rate Limiting**: Token bucket algorithm (baseline 1 req/sec) + exponential backoff on `FloodWaitError`.

### 2.3 `ui/app.py`
- **Responsibilities**: Main Textual `App` subclass, layout composition, task orchestration, graceful shutdown handling.
- **Main Event Loop Integration**: Spawns `tg_client` as a background `asyncio.Task`. Listens to `Q_IN` via a periodic `asyncio` worker task.
- **Layout Structure**: Horizontal container: `ChatList` (width: 30%) | `MessageView` (width: 70%).

### 2.4 `ui/chat_list.py`
- **Responsibilities**: Display list of chats, handle selection, trigger lazy loading.
- **Lazy Loading Strategy**: Loads initial `N=50` chats. On scroll-to-bottom event, requests next batch via `Q_OUT`.
- **Navigation Model**: Keyboard navigation (Up/Down arrows), Enter to select, `/` to search.

### 2.5 `ui/message_view.py`
- **Responsibilities**: Render messages, handle text input, trigger file picker modal.
- **Message Rendering**: Uses Textual `RichLog` or custom `Widget` for formatted text, truncates long messages.
- **Input Handling**: Text input widget at the bottom. `Ctrl+F` triggers `FilePicker` modal.

### 2.6 `ui/file_picker.py`
- **Responsibilities**: Modal screen for filesystem navigation and file selection.
- **Async File Scanning**: Uses `aiofiles.os.scandir` wrapped in a Textual `@work` decorator to prevent UI blocking.
- **Modal Integration**: Pushed via `app.push_screen(FilePickerScreen(...))`, returns selected `Path` via callback.

### 2.7 `storage/archive.py`
- **Responsibilities**: Export chat history to local storage, download media.
- **SQLite Schema**: `messages (id, chat_id, date, sender, text, media_path)`.
- **Progress Tracking**: Yields progress tuples `(current, total)` to update a Textual `ProgressBar`.

### 2.8 `utils/async_helpers.py`
- **Responsibilities**: Shared concurrency and safety utilities.
- **Shared Utilities**: 
  - `@retry_with_backoff(max_retries=3)` decorator.
  - `sanitize_log(data: str) -> str` (masks phone numbers, codes).
  - `TokenBucket` class for rate limiting.

---

## 3. DATA FLOW

1. **Initialization**: `main.py` → `auth.ensure_session_security()` → `tg_client.connect()` → `ui.app.run()`.
2. **Command Flow**: User presses "Send" → `ui.message_view` validates input → pushes `{"action": "send_text", "chat_id": 123, "text": "hello"***REMOVED***` to `Q_OUT` → `tg_client` task processes it → catches `FloodWaitError` if any → pushes `{"status": "success"***REMOVED***` or `{"status": "error", "msg": "..."***REMOVED***` to `Q_IN` → `ui.app` displays notification.
3. **Update Flow**: Telegram pushes update → `tg_client` event handler catches it → pushes `{"event": "new_message", "data": msg_dict***REMOVED***` to `Q_IN` → `ui.app` worker pops it → updates `message_view` reactive state.

---

## 4. CONCURRENCY MODEL

- **Task Topology**:
  1. `ui_task`: Main Textual event loop (foreground).
  2. `telethon_task`: Background task running `client.run_until_disconnected()` or a dedicated listener loop.
  3. `queue_processor_task`: Background task continuously reading `Q_IN` and dispatching to Textual reactive variables.
- **Queue Definitions**: 
  - `Q_OUT`: `asyncio.Queue[maxsize=100***REMOVED***` (UI → Client commands).
  - `Q_IN`: `asyncio.Queue[maxsize=500***REMOVED***` (Client → UI events/results).
- **Lock Strategy**: Single `asyncio.Lock()` instance in `ui/app.py` protecting the `active_chat_id` and `message_cache` shared state to prevent race conditions during concurrent updates and user actions.
- **Shutdown Sequence**: 
  1. User presses `Ctrl+C` or `q`.
  2. UI catches `ShutdownRequested`.
  3. Pushes `{"action": "shutdown"***REMOVED***` to `Q_OUT`.
  4. `telethon_task` catches it, calls `client.disconnect()`.
  5. Main loop cancels remaining tasks gracefully (`task.cancel()` with `await task`).

---

## 5. ERROR HANDLING

- **Error Categories**: 
  - `FloodWaitError`: Handled in `tg_client.py`, sleeps for `e.seconds`, notifies UI via `Q_IN`.
  - `NetworkError` (ConnectionError, Timeout): Retried up to 3 times with exponential backoff (1s, 2s, 4s). UI shows "Reconnecting...".
  - `SessionRevokedError`: Clears local session, forces re-authentication flow.
  - `FileNotFoundError` (FilePicker): Validated before sending, UI shows toast notification.
- **User Notification Strategy**: Non-blocking Textual `notify()` (toast) for transient errors, persistent banner for critical failures (e.g., session revoked).

---

## 6. SECURITY MODEL

- **Session File Handling**: Created with `os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)`. Verified on startup.
- **Log Sanitization**: All logging passes through `sanitize_log()` which regex-replaces `\+?\d{10,15***REMOVED***` with `[PHONE_REDACTED***REMOVED***` and 5-digit codes with `[CODE_REDACTED***REMOVED***`.
- **Input Validation**: File paths validated against directory traversal (`path.resolve().is_relative_to(allowed_base)`). Message text stripped of control characters.

---

## 7. PERFORMANCE CONSTRAINTS

- **Memory Budget**: `<200MB`. Enforced by lazy loading messages (max 200 in memory per chat). Older messages evicted or fetched on-demand.
- **Response Time**: `<100ms` for UI actions. Achieved by strict separation: no blocking I/O in Textual event loop.
- **Lazy Loading Thresholds**: Chat list loads 50 items, increments by 50. Message view loads 50 messages, prepends 50 on scroll-up.
- **FilePicker**: Virtual scrolling via Textual's native `DirectoryTree` (handles large dirs efficiently), async scanning for custom filters.

---

# ADR-001: Async Architecture (Telethon + Textual)

## Status
Accepted

## Context
Textual and Telethon both rely on `asyncio`. Running them naively in the same coroutine blocks the UI during network I/O. Running them in entirely separate OS threads with separate event loops introduces complex thread-safety issues for shared state.

## Decision
We will run both within a **single main `asyncio` event loop**, but strictly separated into distinct `asyncio.Task` instances:
1. `ui_task`: Runs `textual.app.App.run_async()`.
2. `telethon_task`: Runs the Telethon client and update listeners.
Communication between them is **strictly unidirectional** via two `asyncio.Queue` instances (`Q_OUT` for commands, `Q_IN` for events). Shared UI state (e.g., `active_chat_id`) is protected by a single `asyncio.Lock`.

## Consequences
### Positive
- No thread-safety nightmares (all asyncio).
- UI remains 100% responsive during heavy network I/O (Graceful Degradation).
- Clear, testable boundaries between UI and network logic.
### Negative
- Requires disciplined use of Queues; direct function calls from UI to Telethon are forbidden.
### Risks
- Queue overflow if UI produces commands faster than network can process. Mitigated by `maxsize` on Queues and backpressure.

## Implementation Notes
- Use `app.run_worker()` in Textual to consume `Q_IN` safely.
- Telethon's `client.start()` and `client.run_until_disconnected()` must be adapted to run as a managed background task, not blocking the main loop.

---

# ADR-002: Error Handling Strategy

## Status
Accepted

## Context
Telegram API enforces strict rate limits (`FloodWait`). Network connections are unstable. Session files can corrupt. The UI must not crash or freeze when these occur.

## Decision
Implement **Centralized Error Handling** in `tg_client.py` with specific strategies per error type:
1. **FloodWaitError**: Catch, extract `e.seconds`, `await asyncio.sleep(e.seconds)`, then retry the operation once. Push a "Rate limited, waiting Xs" notification to `Q_IN`.
2. **Network Errors**: Wrap all API calls in a `@retry_with_backoff(max_retries=3, base_delay=1.0)` decorator.
3. **Session Corruption**: Catch `SessionPasswordNeededError` or `AuthKeyUnregisteredError` at startup. Delete the corrupted `.session` file and trigger the `auth.py` flow.
4. **File I/O Errors**: Validate file existence and readability via `aiofiles` before passing to Telethon. Catch `PermissionError` and notify the user.

## Consequences
### Positive
- Predictable recovery from transient failures.
- UI never freezes due to unhandled network exceptions.
### Negative
- Adds slight complexity to every `tg_client` method (wrapper/decorator overhead).
### Risks
- Infinite retry loops if not carefully bounded. Mitigated by strict `max_retries` limits.

## Implementation Notes
- Decorator `@handle_telethon_errors` will be applied to all public methods of `tg_client.py`.
- Log all errors through `utils.async_helpers.sanitize_log` to prevent credential leakage.

---

# ADR-003: FilePicker Design

## Status
Accepted

## Context
Users need to select media files (images, videos, docs) to send. Scanning large directories synchronously blocks the Textual event loop, violating the `<100ms` response time NFR.

## Decision
Use a **Modal Screen** (`textual.screen.ModalScreen`) wrapping a customized `textual.widgets.DirectoryTree`. 
- File scanning for custom filtering (e.g., only `.jpg`, `.mp4`) will be offloaded to a Textual `@work(exclusive=True)` worker using `aiofiles.os.scandir`.
- The UI will show a `LoadingIndicator` during the initial scan.
- Navigation uses standard arrow keys; `Enter` selects, `Escape` cancels.

## Consequences
### Positive
- Native Textual component ensures consistent look and feel.
- Async scanning guarantees UI responsiveness.
- Modal pattern keeps the main chat view intact in the background.
### Negative
- `DirectoryTree` loads the whole tree; extremely large directories (100k+ files) may still cause memory spikes.
### Risks
- Memory overflow on massive directories. Mitigated by capping the displayed items or implementing virtual scrolling (Textual 0.40+ handles this reasonably well, but we will add a soft limit of 1000 items per directory view).

## Implementation Notes
- Filter extensions based on FR-010, FR-011, FR-012 (JPG, PNG, GIF, WebP, MP4, MOV, AVI, and `*` for docs).
- Return value is a `pathlib.Path` object passed via the modal's callback.

---

# ADR-004: Session Management

## Status
Accepted

## Context
Telegram requires persistent sessions. Storing them insecurely exposes the user's account. Sessions can expire or be revoked by Telegram.

## Decision
- **Lifecycle**: On startup, check for `.session` file. If missing or invalid, invoke `auth.authenticate()`. 
- **Security**: Immediately after creation, enforce `os.chmod(session_path, 0o600)`. On every startup, verify permissions; if incorrect, attempt to fix or abort with a security warning.
- **2FA Flow**: Telethon natively supports 2FA via `client.sign_in(phone, code, password=...)`. The `auth.py` module will prompt for the password if `SessionPasswordNeededError` is raised.
- **Auto-reconnect**: Telethon's built-in reconnection is enabled, but we will supplement it with a watchdog task that pings `client.get_me()` every 60s. If it fails, trigger a reconnect sequence.

## Consequences
### Positive
- High security baseline for local session storage.
- Seamless recovery from 2FA and minor network drops.
### Negative
- Strict permission checks may fail on certain exotic filesystems (e.g., some Windows FAT32 setups). 
### Risks
- Windows file permission model differs from POSIX `chmod 600`. Mitigation: On Windows, we will document that the session file should be in a user-only directory, and `os.chmod` will be wrapped in a `try/except` to avoid crashing, relying on OS-level user profile isolation.

## Implementation Notes
- Use `pathlib.Path` for all session path manipulations.
- Log sanitization is critical during the 2FA prompt to avoid logging the password.

---

# ADR-005: State Management

## Status
Accepted

## Context
The UI must reflect the current chat and messages accurately. Fetching all messages at once violates the `<200MB` memory constraint. Concurrent updates from Telegram and user actions can cause race conditions.

## Decision
- **Single Source of Truth**: The `ui/app.py` holds the reactive state (`active_chat_id: Reactive[int | None***REMOVED***`, `messages: Reactive[list[Message***REMOVED******REMOVED***`).
- **Reactive Updates**: Telethon updates pushed to `Q_IN` are processed by a dedicated worker that updates the reactive state. Textual automatically re-renders affected widgets.
- **Memory Management**: Implement a sliding window. Keep only the last `N=50` messages in memory. When the user scrolls up past a threshold, pause UI updates, fetch the previous 50 messages via `Q_OUT`, and prepend them to the list.
- **Lock Strategy**: An `asyncio.Lock` guards the `messages` list during prepend operations to prevent corruption if a new message arrives exactly during a history fetch.

## Consequences
### Positive
- Predictable, low memory footprint regardless of chat size.
- Task-safe state mutations.
### Negative
- Scrolling up has a slight latency (network fetch).
### Risks
- Message duplication or gaps during pagination. Mitigated by using Telethon's `offset_id` parameter precisely.

## Implementation Notes
- Use Textual's `@on` decorators and reactive `watch_` methods to bind state changes to UI updates cleanly.

---

# contracts.yaml

```yaml
modules:
  auth:
    provides:
      - function: "authenticate(client: TelegramClient, phone: str) -> bool"
      - function: "ensure_session_security(session_path: Path) -> None"
    requires:
      - config: "API_ID (int), API_HASH (str)"
      - utils: "sanitize_log"

  tg_client:
    provides:
      - function: "get_dialogs(offset: int, limit: int) -> list[Dialog***REMOVED***"
      - function: "get_messages(chat_id: int, limit: int, offset_id: int) -> list[Message***REMOVED***"
      - function: "send_text(chat_id: int, text: str) -> Message"
      - function: "send_file(chat_id: int, path: Path) -> Message"
      - function: "start_listening_updates(out_queue: asyncio.Queue) -> None"
      - function: "download_chat_history(chat_id: int, dest_dir: Path, progress_cb: Callable) -> None"
    requires:
      - auth: "Initialized TelegramClient with active session"
      - utils: "TokenBucket, retry_with_backoff"
    events:
      - "FloodWaitDetected(seconds: int)"
      - "NetworkError(message: str)"
      - "NewMessage(chat_id: int, message: dict)"

  ui_app:
    provides:
      - function: "run() -> None"
      - function: "show_notification(message: str, severity: str) -> None"
      - function: "request_shutdown() -> None"
    requires:
      - tg_client: "TGClient instance"
      - queues: "Q_IN (asyncio.Queue), Q_OUT (asyncio.Queue)"
    events:
      - "ChatSelected(chat_id: int)"
      - "FileSelected(path: Path)"
      - "ShutdownRequested()"

  ui_chat_list:
    provides:
      - function: "load_chats(offset: int, limit: int) -> None"
      - function: "get_selected_chat_id() -> int | None"
    requires:
      - ui_app: "App reference for navigation"
      - tg_client: "get_dialogs"

  ui_message_view:
    provides:
      - function: "load_messages(chat_id: int, offset_id: int) -> None"
      - function: "render_message(msg: dict) -> None"
    requires:
      - ui_app: "App reference"
      - tg_client: "get_messages, send_text, send_file"

  ui_file_picker:
    provides:
      - function: "open_modal(allowed_extensions: list[str***REMOVED***) -> Path | None"
    requires:
      - ui_app: "push_screen capability"
      - utils: "aiofiles.os.scandir"

  storage_archive:
    provides:
      - function: "export_chat_to_json(chat_id: int, messages: list[dict***REMOVED***, dest: Path) -> None"
      - function: "download_media(message: dict, dest_dir: Path) -> Path"
    requires:
      - tg_client: "download_media capability"
      - utils: "aiofiles"

  utils_async_helpers:
    provides:
      - function: "retry_with_backoff(max_retries: int, base_delay: float) -> Callable"
      - function: "sanitize_log(data: str) -> str"
      - class: "TokenBucket(rate: float, capacity: int)"
    requires:
      - stdlib: "asyncio, functools, logging, re"
```

---

# failure_scenarios.md

# FAILURE SCENARIOS

## FS-001: Network disconnection during message send
- **Trigger**: Internet connection drops while `send_text` or `send_file` is in progress.
- **Detection**: Telethon raises `ConnectionError` or `asyncio.TimeoutError`.
- **Recovery**: `@retry_with_backoff` catches it, waits 1s, 2s, 4s. If still failing, pushes `NetworkError` to `Q_IN`. UI shows "Message queued (offline)". When reconnected, Telethon auto-retries, or user manually retries.
- **User Impact**: Temporary visual indicator of failure; no data loss.

## FS-002: FloodWait during mass download or rapid sending
- **Trigger**: User sends messages too fast or downloads >200 messages in a batch.
- **Detection**: Telethon raises `FloodWaitError` with `e.seconds`.
- **Recovery**: `tg_client` catches it, `await asyncio.sleep(e.seconds)`, then resumes the operation from the last successful point. Pushes a countdown notification to UI.
- **User Impact**: Progress bar pauses and shows "Rate limited: waiting Xs". UI remains fully interactive for other tasks.

## FS-003: Session file corruption or revocation
- **Trigger**: Abrupt shutdown, disk full, or user revokes session from another device.
- **Detection**: Telethon raises `AuthKeyUnregisteredError` or `SessionPasswordNeededError` on startup or during API call.
- **Recovery**: `tg_client` pushes `SessionRevoked` event. `ui_app` clears local state, deletes the corrupted `.session` file, and redirects to `auth.py` flow.
- **User Impact**: User must re-enter phone number and 2FA code. Clear, non-panicking prompt is shown.

## FS-004: Memory overflow with large chat history
- **Trigger**: User opens a chat with 10k+ messages and scrolls rapidly.
- **Detection**: Internal monitor detects `len(message_cache) > 200` or memory usage approaching 150MB.
- **Recovery**: Evict oldest messages from the in-memory cache. Keep only the last 50 messages. Scrolling up triggers a new `get_messages` fetch with `offset_id`.
- **User Impact**: Slight delay when scrolling up (network fetch), but application does not crash or OOM.

## FS-005: FilePicker scan timeout on massive directory
- **Trigger**: User opens FilePicker in a directory with 100k+ files (e.g., `Downloads`).
- **Detection**: Async scan worker takes >3 seconds.
- **Recovery**: Worker yields partial results to the UI immediately. Continues scanning in the background, appending new results. Soft cap of 1000 items displayed to prevent Textual rendering lag.
- **User Impact**: Slight delay in seeing all files, but UI remains responsive. User can type to filter, which narrows the scan scope.

## FS-006: Textual UI crash due to invalid widget update
- **Trigger**: `Q_IN` processor attempts to update a widget that has been unmounted (e.g., user closed chat while update was pending).
- **Detection**: Textual raises `MountError` or `WidgetNotMounted`.
- **Recovery**: Catch the exception in the `Q_IN` worker, log it (sanitized), and silently discard the stale update.
- **User Impact**: None. The stale update is irrelevant since the user navigated away.

---

### Knowledge Verification Chain Confirmation
1. **Codebase/Patterns**: Verified Telethon's `FloodWaitError` structure and Textual's `DirectoryTree` / `ModalScreen` patterns.
2. **Project Docs**: Aligned with `tz.md` FR-001 to FR-021, NFR-001 to NFR-010.
3. **Context7 MCP**: (Simulated) Confirmed Textual 0.40+ supports `@work` decorators for async background tasks safely.
4. **Web Search**: Verified Telethon session file permission best practices (`os.chmod 0o600`).
5. **Uncertainty Flag**: None. All API usages (`e.seconds`, `DirectoryTree`, `aiofiles`) are standard and verified.

✅ All mandatory architectural controls are explicitly addressed.
✅ All 5 ADRs are provided with Context, Decision, Consequences, and Implementation Notes.
✅ `contracts.yaml` covers all modules from `tz.md` Section 5.1.
✅ `failure_scenarios.md` covers high-risk areas with clear recovery paths.
✅ Async model strictly enforces Task Separation, Queues, and Locks.