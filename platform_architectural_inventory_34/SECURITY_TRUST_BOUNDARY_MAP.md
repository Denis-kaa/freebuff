# SECURITY / TRUST BOUNDARY MAP — promt107 §14 forensic

> Вопрос: может ли внешний проект/мост получить shell / filesystem / secrets /
> вызвать внутренний tool / Forge / другой Project / Workspace / выйти из sandbox.

## Границы доверия (факт)

```
┌─────────────────────────────────────────────────────────────┐
│ TRUSTED: локальный CLI (Termux, владелец устройства)        │
│  - полный filesystem, shell, все инструменты                │
└───────────────────────┬─────────────────────────────────────┘
                        │ (нет sandbox — единая доверенная зона)
┌───────────────────────▼─────────────────────────────────────┐
│ SEMI-TRUSTED: MCP HTTP (:8765)  — mcp_fastapi.py            │
│  - Bearer-token auth (Vault-backed, TTL cache)              │
│  - env fallback FREEBUFF_VAULT_TOKEN / FREEBUFF_VAULT_KEY   │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ SEMI-TRUSTED: Telegram (TG bot / client)                    │
│  - telegram_contract.py wrapper (chat_id-bound)             │
│  - telegram_bot.py (getUpdates)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│ SEMI-TRUSTED: Phone MCP (send_sms/get_contacts/play_music)  │
│  - phone_control_mcp.py                                     │
└─────────────────────────────────────────────────────────────┘
```

## Ответы на вопросы §14

| Вопрос | Ответ | Evidence |
|--------|-------|----------|
| Внешний проект → shell? | **ДА (риск).** `tool_runtime.py::ShellTool` выполняет `subprocess.run(cmd)` без sandbox. Но ShellTool НЕ зарегистрирован в MCP server по умолчанию (MCP-инструменты = свои `McpTool`, не ToolRegistry). | tool_runtime.py:550-605 |
| Внешний → filesystem? | **ДА (риск).** `FileTool` читает/пишет файлы; `phone_control_mcp` — локальные операции. Ограничение только на уровне вызова. | tool_runtime.py:393 |
| Внешний → secrets? | **ЧАСТИЧНО.** `mcp_fastapi.py` Bearer+Vault (approle login, TTL). Но `mcp_server.py` (stdio/JSON-RPC) НЕ имеет auth — локальный. `.keys/` gitignored. | mcp_fastapi.py:202-277 |
| Внешний → внутренний tool? | **ДА через MCP.** `BuffyMcpServer.handle_tools_call` диспатчит любые зарегистрированные MCP-инструменты. Shell/File не по умолчанию. | mcp_server.py:2510 |
| Внешний → Forge? | **НЕ напрямую.** Forge запускается через `ForgeFacade`/`forge.py` CLI, НЕ экспонирован как MCP-инструмент. | (отсутствие MCP-tool для forge) |
| Внешний → другой Project? | **PARTIAL guard.** `WorkspaceRegistry.assert_path_privacy` → `PrivacyViolationError` (path = один workspace). | workspace_registry.py:assert_path_privacy |
| Внешний → Workspace? | **PARTIAL.** workspace owner_chat_id = 0 (не привязан); privacy guard на project-path, не на workspace-level authz. | workspace_registry.py |
| Выйти из sandbox? | **N/A — sandbox отсутствует.** Вся платформа в единой доверенной зоне Termux. | — |

## Слабые места (TRUST BOUNDARY GAPS)

1. **Нет sandbox / network isolation** — весь код в одном процессе/файловой системе.
2. **`mcp_server.py` без auth** (stdio-local, но если проброшен наружу — открыт).
3. **`owner_chat_id=0`** — workspace не привязан к владельцу → нет tenant isolation.
4. **Tool permissions** — нет per-tool ACL (ShellTool доступен любому локальному вызывающему).
5. **Нет audit-trail для tool-вызовов** (event_log есть только для ScenarioIntelligence, не для tool/forge).
6. **Secret storage** — `.env` + `.keys/` (gitignored) + Vault для MCP; консистентного хранилища нет.
