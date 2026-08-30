"""
Freebuff Plugin — Telegram Bot with Scenario Engine Integration.

Команды:
  /start                 — приветствие и справка
  /scenarios             — меню сценариев (inline keyboard)
  /scenarios list        — список всех сценариев
  /scenarios list <cat>  — сценарии категории (freelancing, agent, templates)
  /scenarios apply <slug> — применить сценарий
  /scenarios search <q>  — поиск сценариев
  /status                — статус системы

Inline кнопки:
  Категории → сценарии → детали → применить
  Навигация "← Назад" между уровнями

Использование:
  TELEGRAM_BOT_TOKEN=xxx python freebuff_plugin_03/tgbot.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
}
from typing import Any

}
import time as _time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ── Пути ─────────────────────────────────────────────────────

FREEBUFF_ROOT = Path(os.environ.get(
    "FREEBUFF_ROOT",
    str(Path(__file__).resolve().parent.parent),
))
sys.path.insert(0, str(FREEBUFF_ROOT))

from freebuff_plugin_03.scenario_engine import ScenarioEngine
from scripts_01.tgbot_base import BaseTGBot, load_dotenv
from core_02.telegram_contract import (
    SAVED_MESSAGES_CHAT_ID,
    LITVINOV_CHAT_ID,
    report_to_saved_messages,
    report_to_alex_litvinov,
)

# ── Логирование ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("freebuff.tgbot")

# ── Токен ────────────────────────────────────────────────────

# .env загружается в BaseTGBot.__init__ (DEBT-007); ранний вызов — для
# модульного уровня (main() берёт bot_instance.token).
load_dotenv(FREEBUFF_ROOT / ".env")

# ── Callback data префиксы ───────────────────────────────────

CALLBACK_PREFIXES = {
    "CAT": "sc_cat_",       # выбор категории
    "SC": "sc_sc_",         # выбор сценария
    "APPLY": "sc_apply_",   # применить сценарий
    "BACK_CAT": "sc_back_cat",   # назад к категориям
    "BACK_SC": "sc_back_sc_",    # назад к списку сценариев в категории
    "VARS": "sc_vars_",     # запросить переменные
}

# ═══════════════════════════════════════════════════════════════
# Bot
# ═══════════════════════════════════════════════════════════════

class ScenarioTGBot(BaseTGBot):
    """Telegram бот для навигации и применения сценариев.

    Наследует общую Telegram-инфраструктуру (BaseTGBot): .env-загрузку,
    токен, ApplicationBuilder, polling-цикл и error handler (DEBT-007).
    """

    logger = logging.getLogger("freebuff.tgbot")

    def __init__(self):
        super().__init__(FREEBUFF_ROOT)
        self.engine = ScenarioEngine()
        # Хранилище временных состояний: {chat_id: {slug, step, timestamp}}
        self._states: dict[int, dict[str, Any]] = {}
        self._max_states = 1000  # макс. записей в _states
        self._state_ttl = 600   # 10 минут — время жизни состояния

    # ── Очистка устаревших состояний ────────────────────────

    def _prune_states(self) -> None:
        """Удаляет устаревшие состояния (старше _state_ttl секунд)."""
        now = _time.time()
        stale = [
            cid for cid, st in self._states.items()
            if _time.time() - st.get("timestamp", 0) > self._state_ttl
        ]
        for cid in stale:
            del self._states[cid]
        # Если всё ещё больше лимита — удаляем самые старые
        if len(self._states) > self._max_states:
            sorted_cids = sorted(
                self._states.keys(),
                key=lambda cid: self._states[cid].get("timestamp", 0),
            )
            excess = len(self._states) - self._max_states
            for cid in sorted_cids[:excess]:
                del self._states[cid]

    def _set_state(self, chat_id: int, data: dict[str, Any]) -> None:
        """Устанавливает состояние с временем жизни."""
        self._prune_states()
        data["timestamp"] = _time.time()
        self._states[chat_id] = data

    def _get_state(self, chat_id: int) -> dict[str, Any] | None:
        """Возвращает состояние, если оно не устарело."""
        state = self._states.get(chat_id)
        if state is None:
            return None
        if _time.time() - state.get("timestamp", 0) > self._state_ttl:
            del self._states[chat_id]
            return None
        return state

    def _del_state(self, chat_id: int) -> None:
        """Удаляет состояние."""
        self._states.pop(chat_id, None)

    # ── Вспомогательные методы ──────────────────────────────

    def _get_categories(self) -> list[str]:
        """Возвращает список уникальных категорий сценариев."""
        scenarios = self.engine.list_scenarios()
        cats: set[str] = set()
        for s in scenarios:
            if s.get("category"):
                cats.add(s["category"])
        return sorted(cats)

    def _scenarios_by_category(self, category: str) -> list[dict[str, Any]]:
        """Сценарии в категории."""
        return self.engine.list_scenarios(category=category)

    def _format_scenario_list(self, scenarios: list[dict[str, Any]], show_category: bool = True) -> str:
        """Форматирует список сценариев для сообщения."""
        if not scenarios:
            return "😕 Нет сценариев."
        
        lines = []
        for s in scenarios:
            tags = f"[{', '.join(s.get('tags', []))}]" if s.get('tags') else ""
            cat = f" [{s['category']}]" if show_category and s.get('category') else ""
            lines.append(
                f"• *{s['title']}*{cat}\n"
                f"  `{s['slug']}` — {s.get('description', '')[:100]}"
            )
        return "\n\n".join(lines)

    def _format_scenario_detail(self, scenario: dict[str, Any]) -> str:
        """Форматирует детали одного сценария."""
        tags = ", ".join(scenario.get("tags", []))
        return (
            f"📋 *{scenario['title']}*\n\n"
            f"🔖 Slug: `{scenario['slug']}`\n"
            f"📂 Категория: {scenario.get('category', '—')}\n"
            f"⚙️ Сложность: {scenario.get('complexity', '—')}\n"
            f"🏷️ Теги: {tags or '—'}\n\n"
            f"📝 *Описание:*\n{scenario.get('description', '—')[:300]}"
        )

    # ── Inline клавиатуры ───────────────────────────────────

    def _categories_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура выбора категории."""
        buttons = []
        for cat in self._get_categories():
            scenarios = self._scenarios_by_category(cat)
            emoji = {
                "freelancing": "💼",
                "agent": "🤖",
                "templates": "📝",
            ].get(cat, "📁")
            count = len(scenarios)
            buttons.append([
                InlineKeyboardButton(
                    f"{emoji} {cat.capitalize()} ({count})",
                    callback_data=f"{CALLBACK_PREFIXES['CAT']}{cat}",
                )
            ])
        buttons.append([
            InlineKeyboardButton("📋 Все сценарии", callback_data=f"{CALLBACK_PREFIXES['CAT']}all"),
        ])
        buttons.append([
            InlineKeyboardButton("🔍 Поиск", switch_inline_query_current_chat="/scenarios search "),
        ])
        return InlineKeyboardMarkup(buttons)

    def _scenarios_keyboard(self, category: str) -> InlineKeyboardMarkup:
        """Клавиатура со сценариями в категории."""
        if category == "all":
            scenarios = self.engine.list_scenarios()
        else:
            scenarios = self._scenarios_by_category(category)
        
        buttons = []
        for s in scenarios:
            buttons.append([
                InlineKeyboardButton(
                    f"{s['title'][:40]}",
                    callback_data=f"{CALLBACK_PREFIXES['SC']}{s['slug']}",
                )
            ])
        buttons.append([
            InlineKeyboardButton("← Назад к категориям", callback_data=CALLBACK_PREFIXES["BACK_CAT"]),
        ])
        return InlineKeyboardMarkup(buttons)

    def _scenario_detail_keyboard(self, slug: str, category: str) -> InlineKeyboardMarkup:
        """Клавиатура действий для сценария."""
        scenario = self.engine.get_scenario(slug)
        buttons = []
        if scenario and scenario.prompt_template:
            buttons.append([
                InlineKeyboardButton(
                    "🚀 Применить",
                    callback_data=f"{CALLBACK_PREFIXES['APPLY']}{slug}",
                )
            ])
        buttons.append([
            InlineKeyboardButton("← Назад", callback_data=f"{CALLBACK_PREFIXES['BACK_SC']}{category}"),
        ])
        return InlineKeyboardMarkup(buttons)

    def _variables_keyboard(self, slug: str) -> InlineKeyboardMarkup:
        """Клавиатура для ввода переменных."""
        buttons = [
            [
                InlineKeyboardButton("✅ Без переменных", callback_data=f"{CALLBACK_PREFIXES['VARS']}{slug}"),
            ],
            [
                InlineKeyboardButton("← Назад", callback_data=f"{CALLBACK_PREFIXES['SC']}{slug}"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    def _home_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура главного меню."""
        buttons = [
            [InlineKeyboardButton("📋 Сценарии", callback_data=CALLBACK_PREFIXES["BACK_CAT"])],
            [
                InlineKeyboardButton("💬 Статус", callback_data="sc_status"),
                InlineKeyboardButton("❓ Помощь", callback_data="sc_help"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ── Получение шаблона переменных ─────────────────────────

    def _extract_variable_names(self, prompt_template: str) -> list[str]:
        """Извлекает имена переменных из {placeholders]."""
        return list(set(re.findall(r"\{(\w+)\*)", prompt_template)))

    # ═══════════════════════════════════════════════════════════
    # Команды
    # ═══════════════════════════════════════════════════════════

    # ── /start ──

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Приветствие и справка."""
        text = (
            "🤖 *Freebuff Plugin — Telegram Bot*\n\n"
            "Управляй сценариями разработки через Telegram.\n\n"
            "*Команды:*\n"
            "`/scenarios` — Меню сценариев (интерактивные кнопки)\n"
            "`/scenarios list` — Список всех сценариев\n"
            "`/scenarios list <категория>` — Сценарии категории\n"
            "`/scenarios apply <slug>` — Применить сценарий\n"
            "`/scenarios search <запрос>` — Поиск сценариев\n"
            "`/status` — Статус бота\n\n"
            f"📚 Всего сценариев: {len(self.engine.list_scenarios())}"
        )
        await update.effective_message.reply_text(
            text,
            reply_markup=self._home_keyboard(),
            parse_mode="Markdown",
        )

    # ── /status ──

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Статус системы."""
        scenarios = self.engine.list_scenarios()
        cats = self._get_categories()
        cat_lines = "\n".join(f"  • {c}: {len(self._scenarios_by_category(c))}" for c in cats)
        text = (
            "📊 *Freebuff Plugin Status*\n\n"
            f"📚 Сценариев: {len(scenarios)}\n"
            f"📂 Категории:\n{cat_lines}\n\n"
            f"🔄 Перезагрузить: /reload"
        )
        await update.effective_message.reply_text(
            text,
            parse_mode="Markdown",
        )

    # ── /scenarios ──

    async def cmd_scenarios(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Главный хендлер /scenarios с поддержкой подкоманд.
        /scenarios              — меню (inline keyboard)
        /scenarios list         — список всех
        /scenarios list <cat>   — список категории
        /scenarios apply <slug> — применить
        /scenarios search <q>   — поиск
        """
        args = context.args or []

        # Нет аргументов → меню категорий
        if not args:
            text = (
                "📋 *Сценарии разработки*\n\n"
                "Выбери категорию, чтобы увидеть доступные сценарии:"
            )
            await update.effective_message.reply_text(
                text,
                reply_markup=self._categories_keyboard(),
                parse_mode="Markdown",
            )
            return

        subcommand = args[0].lower()

        if subcommand == "list":
            await self._handle_list(update, args[1:], context)
        elif subcommand == "apply":
            await self._handle_apply(update, args[1:], context)
        elif subcommand == "search":
            await self._handle_search(update, args[1:], context)
        else:
            await update.effective_message.reply_text(
                f"Неизвестная подкоманда: `{subcommand}`\n"
                "Доступно: `list`, `apply`, `search`\n"
                "Пример: `/scenarios list`",
                parse_mode="Markdown",
            )

    # ── Подкоманды /scenarios ──

    async def _handle_list(self, update: Update, args: list[str], context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка /scenarios list [category]."""
        category = " ".join(args).strip() if args else None

        if category:
            scenarios = self.engine.list_scenarios(category=category)
            if not scenarios:
                await update.effective_message.reply_text(
                    f"😕 В категории «{category}» нет сценариев.\n"
                    f"Доступные категории: {', '.join(self._get_categories())}",
                )
                return
            text = f"📋 *Сценарии: {category}*\n\n" + self._format_scenario_list(scenarios, show_category=False)
            await update.effective_message.reply_text(
                text,
                reply_markup=self._scenarios_keyboard(category),
                parse_mode="Markdown",
            )
        else:
            await update.effective_message.reply_text(
                "📋 *Все сценарии*\n\n" + self._format_scenario_list(self.engine.list_scenarios()),
                reply_markup=self._scenarios_keyboard("all"),
                parse_mode="Markdown",
            )

    async def _handle_apply(self, update: Update, args: list[str], context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка /scenarios apply <slug> [var=value ...]."""
        if not args:
            await update.effective_message.reply_text(
                "Укажи slug сценария:\n"
                "`/scenarios apply freelance_parser`\n"
                "`/scenarios apply freelance_parser URL=https://...`",
                parse_mode="Markdown",
            )
            return

        slug = args[0]
        scenario = self.engine.get_scenario(slug)
        if not scenario:
            await update.effective_message.reply_text(
                f"😕 Сценарий `{slug}` не найден.\n"
                f"Доступные: {', '.join(s.slug for s in self.engine._scenarios.values())}",
                parse_mode="Markdown",
            )
            return

        # Извлекаем переменные из аргументов
        variables: dict[str, str] = {}
        for arg in args[1:]:
            if "=" in arg:
                k, _, v = arg.partition("=")
                variables[k.strip()] = v.strip()

        # Если есть неподставленные переменные — показываем список
        var_names = self._extract_variable_names(scenario.prompt_template)
        missing = [v for v in var_names if v not in variables]

        if missing and not variables:
            var_list = "\n".join(f"  • `{v}`" for v in missing)
            text = (
                f"📋 *{scenario.title}*\n\n"
                f"🔖 Slug: `{scenario.slug}`\n\n"
                f"Для применения укажи переменные:\n{var_list}\n\n"
                f"Пример:\n"
                f"`/scenarios apply {scenario.slug} {'=значение '.join(missing)}={'значение' * bool(missing)}`"
            )
            await update.effective_message.reply_text(
                text,
                reply_markup=self._variables_keyboard(slug),
                parse_mode="Markdown",
            )
            return

        # Применяем
        result = self.engine.apply_scenario(slug, variables if variables else None)
        if "error" in result:
            await update.effective_message.reply_text(f"❌ {result['error']}")
            return

        prompt = result["prompt"]
        await self._send_prompt(update, prompt, slug, result["title"])

    async def _handle_search(self, update: Update, args: list[str], context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка /scenarios search <query>."""
        query = " ".join(args).strip() if args else ""
        if not query:
            await update.effective_message.reply_text(
                "Укажи поисковый запрос:\n"
                "`/scenarios search telegram`\n"
                "`/scenarios search parser`",
                parse_mode="Markdown",
            )
            return

        results = self.engine.search_scenarios(query)
        if not results:
            await update.effective_message.reply_text(
                f"😕 По запросу «{query}» ничего не найдено."
            )
            return

        text = f"🔍 *Результаты поиска: «{query}»* ({len(results)})\n\n"
        text += self._format_scenario_list(results)
        await update.effective_message.reply_text(
            text,
            parse_mode="Markdown",
        )

    @staticmethod
    async def _send_prompt_result(
        reply_or_edit: Any, prompt: str, slug: str, title: str, is_edit: bool = False
    ) -> None:
        """Отправить промт (текстом если ≤ 4000, иначе документом).

        reply_or_edit — Message (reply) или CallbackQuery (edit).
        """
        max_len = 4000
        if len(prompt) <= max_len:
            kwargs = {
                "text": f"✅ *Сценарий применён*\n\n```\n{prompt}\n```",
                "parse_mode": "Markdown",
            }
            if is_edit:
                await reply_or_edit.edit_message_text(**kwargs)
            else:
                await reply_or_edit.reply_text(**kwargs)
        else:
            text_preview = (
                f"✅ *Сценарий применён*\n📏 Промт ({len(prompt)} символов) — "
                f"отправляю файлом..."
            )
            if is_edit:
                await reply_or_edit.edit_message_text(text_preview, parse_mode="Markdown")
            else:
                await reply_or_edit.reply_text(text_preview, parse_mode="Markdown")
            # Отправляем файлом
            if is_edit:
                await reply_or_edit.message.reply_document(
                    document=prompt.encode("utf-8"),
                    filename=f"{slug}_prompt.md",
                    caption=f"📋 {title} — готовый промт",
                )
            else:
                await reply_or_edit.reply_document(
                    document=prompt.encode("utf-8"),
                    filename=f"{slug}_prompt.md",
                    caption=f"📋 {title} — готовый промт",
                )

    async def _send_prompt(
        self, update: Update, prompt: str, slug: str, title: str
    ) -> None:
        """Отправить промт (через reply)."""
        await self._send_prompt_result(
            update.effective_message, prompt, slug, title, is_edit=False
        )

    async def cmd_reload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Перезагрузить сценарии. /reload"""
        count = self.engine.reload()
        await update.effective_message.reply_text(
            f"🔄 Сценарии перезагружены. Загружено: {count}",
        )

    # ── /escalate ──

    async def cmd_escalate(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Эскалировать текущий сценарий клиенту (Александр Литвинов). /escalate [note]

        Wire‑in point: report_to_alex_litvinov из core_02/telegram_contract.jl
        — закрывает CAN‑3 contract per LESSONS §10 — реальный Telegram‑ack
        клиенту вместо Telegram‑only admin‑loop.
        """
        chat_id = update.effective_chat.id if update.effective_chat else None
        note = " ".join(context.args or []).strip()

        scenarios = self.engine.list_scenarios()
        ts = _time.strftime("%Y-%m-%d %H:%M:%S", _time.gmtime())
        escalation_text = (
            "🚨 [Freebuff escalation] (TEST CYCLE)\n\n"
            f"🕐 Time (UTC): {ts}\n"
            f"📨 Source chat_id: {chat_id}\n"
            f"📚 Loaded scenarios: {len(scenarios)}\n"
            f"💬 Note: {note or '(none)'}\n\n"
            "Это тестовое сообщение от ScenarioTGBot /escalate — закрывает "
            "LESSONS §10 TG‑contract (post CAN‑3 closure v5.40.0+E2E v5.41.0)."
        )

        try:
            msg_id = await report_to_alex_litvinov(escalation_text)
            if msg_id is None:
                await update.effective_message.reply_text(
                    "⚠️ Escalation не доставлена — TGClient недоступен или сессия "
                    "не авторизована. Проверь `python scripts_01/tg_smoke.py` для diagnostics."
                )
                return
            await update.effective_message.reply_text(
                f"🚨 Escalation доставлена клиенту. msg_id={msg_id}"
            )
        except Exception as exc:
            logger.exception("escalate failed")
            await update.effective_message.reply_text(f"❌ Escalation error: {exc}")

    # ── Текст без команды ──

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка произвольного текста."""
        text = update.message.text or ""
        chat_id = update.effective_chat.id if update.effective_chat else None

        # Проверяем, ожидаем ли мы ввод переменных для сценария
        if chat_id:
            state = self._get_state(chat_id)
        else:
            state = None

        if state and state.get("step") == "wait_vars":
                # Парсим ввод пользователя как переменные
                try:
                    variables = json.loads(text)
                except json.JSONDecodeError:
                    # Пробуем формат ключ=значение строка за строкой
                    variables = {}
                    for line in text.split("\n"):
                        line = line.strip()
                        if "=" in line:
                            k, _, v = line.partition("=")
                            variables[k.strip()] = v.strip()

                # Проверка на команду "готово" — применить без переменных
                if text.strip().lower() in ("готово", "да", "yes", "done", "apply"):
                    variables = {}
                elif not variables:
                    # Применяем без переменных
                    variables = {}

                slug = state["slug"]
                result = self.engine.apply_scenario(slug, variables)
                self._del_state(chat_id)

                if "error" in result:
                    await update.effective_message.reply_text(f"❌ {result['error']}")
                    return

                await self._send_prompt(
                    update, result["prompt"], slug, result["title"]
                )
                return

        # Иначе — приветствие
        await update.effective_message.reply_text(
            "Я бот для работы со сценариями Freebuff Plugin.\n"
            "Используй /scenarios для просмотра сценариев.\n"
            "Или /start для справки.",
        )

    # ═══════════════════════════════════════════════════════════
    # Inline Callback обработчики
    # ═══════════════════════════════════════════════════════════

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обрабатывает нажатия на inline кнопки."""
        query = update.callback_query
        await query.answer()
        data = query.data
        chat_id = update.effective_chat.id if update.effective_chat else 0

        # ── Статус ──
        if data == "sc_status":
            scenarios = self.engine.list_scenarios()
            cats = self._get_categories()
            cat_lines = "\n".join(f"  • {c}: {len(self._scenarios_by_category(c))}" for c in cats)
            text = (
                "📊 *Freebuff Plugin Status*\n\n"
                f"📚 Сценариев: {len(scenarios)}\n"
                f"📂 Категории:\n{cat_lines}"
            )
            await query.edit_message_text(text, parse_mode="Markdown")

        # ── Помощь ──
        elif data == "sc_help":
            text = (
                "🤖 *Freebuff Plugin — Telegram Bot*\n\n"
                "*Команды:*\n"
                "`/scenarios` — Меню сценариев\n"
                "`/scenarios list` — Список сценариев\n"
                "`/scenarios apply <slug>` — Применить сценарий\n"
                "`/scenarios search <запрос>` — Поиск\n"
                "`/status` — Статус\n\n"
                "Просто нажимай на кнопки для навигации! 👇"
            )
            await query.edit_message_text(text, parse_mode="Markdown")

        # ── Выбор категории ──
        elif data.startswith(CALLBACK_PREFIXES["CAT"]):
            category = data[len(CALLBACK_PREFIXES["CAT"]):]
            if category == "all":
                scenarios = self.engine.list_scenarios()
                cat_display = "все"
            else:
                scenarios = self._scenarios_by_category(category)
                cat_display = category

            if not scenarios:
                await query.edit_message_text(
                    f"😕 В категории «{cat_display}» нет сценариев.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("← Назад", callback_data=CALLBACK_PREFIXES["BACK_CAT"]),
                    ]]),
                )
                return

            text = f"📋 *Сценарии: {cat_display}*\n\n" + self._format_scenario_list(scenarios, show_category=False)
            await query.edit_message_text(
                text,
                reply_markup=self._scenarios_keyboard(category),
                parse_mode="Markdown",
            )

        # ── Выбор сценария → детали ──
        elif data.startswith(CALLBACK_PREFIXES["SC"]):
            slug = data[len(CALLBACK_PREFIXES["SC"]):]
            scenario = self.engine.get_scenario(slug)
            if not scenario:
                await query.edit_message_text(f"😕 Сценарий {slug} не найден.")
                return

            detail = self._format_scenario_detail(scenario.to_dict())
            has_template = bool(scenario.prompt_template)
            if not has_template:
                detail += "\n\n⚠️ *У этого сценария нет готового промта для применения.*"

            await query.edit_message_text(
                detail,
                reply_markup=self._scenario_detail_keyboard(slug, scenario.category),
                parse_mode="Markdown",
            )

        # ── Применить сценарий ──
        elif data.startswith(CALLBACK_PREFIXES["APPLY"]):
            slug = data[len(CALLBACK_PREFIXES["APPLY"]):]
            scenario = self.engine.get_scenario(slug)
            if not scenario:
                await query.edit_message_text(f"😕 Сценарий {slug} не найден.")
                return

            # Извлекаем переменные из шаблона
            var_names = self._extract_variable_names(scenario.prompt_template)
            if not var_names:
                # Нет переменных — применяем сразу
                result = self.engine.apply_scenario(slug)
                await self._send_prompt_result(
                    query, result["prompt"], slug, scenario.title, is_edit=True
                )
            else:
                # Просим ввести переменные
                self._set_state(chat_id, {"slug": slug, "step": "wait_vars"})
                
                var_list = "\n".join(f"  • `{v}` = значение" for v in var_names)
                text = (
                    f"✏️ *Введи переменные для «{scenario.title}»*\n\n"
                    f"Необходимые переменные:\n{var_list}\n\n"
                    f"Отправь в формате:\n"
                    f"`ключ1=значение1`\n"
                    f"`ключ2=значение2`\n\n"
                    f"Или отправь `готово` чтобы применить без переменных."
                )
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Применить без переменных", callback_data=f"{CALLBACK_PREFIXES['VARS']}{slug}"),
                    ], [
                        InlineKeyboardButton("← Назад", callback_data=CALLBACK_PREFIXES["BACK_SC"] + scenario.category),
                    ]]),
                    parse_mode="Markdown",
                )

        # ── Применить без/с переменными ──
        elif data.startswith(CALLBACK_PREFIXES["VARS"]):
            slug = data[len(CALLBACK_PREFIXES["VARS"]):]
            scenario = self.engine.get_scenario(slug)
            if not scenario:
                await query.edit_message_text(f"😕 Сценарий {slug} не найден.")
                return

            result = self.engine.apply_scenario(slug)
            # Очищаем состояние
            self._del_state(chat_id)
            await self._send_prompt_result(
                query, result["prompt"], slug, scenario.title, is_edit=True
            )

        # ── Назад к категориям ──
        elif data == CALLBACK_PREFIXES["BACK_CAT"]:
            text = "📋 *Сценарии разработки*\n\nВыбери категорию:"
            await query.edit_message_text(
                text,
                reply_markup=self._categories_keyboard(),
                parse_mode="Markdown",
            )

        # ── Назад к списку сценариев в категории ──
        elif data.startswith(CALLBACK_PREFIXES["BACK_SC"]):
            category = data[len(CALLBACK_PREFIXES["BACK_SC"]):]
            if not category or category == "all":
                scenarios = self.engine.list_scenarios()
                text = "📋 *Все сценарии*\n\n" + self._format_scenario_list(scenarios)
                await query.edit_message_text(
                    text,
                    reply_markup=self._scenarios_keyboard("all"),
                    parse_mode="Markdown",
                )
            else:
                scenarios = self._scenarios_by_category(category)
                text = f"📋 *Сценарии: {category}*\n\n" + self._format_scenario_list(scenarios, show_category=False)
                await query.edit_message_text(
                    text,
                    reply_markup=self._scenarios_keyboard(category),
                    parse_mode="Markdown",
                )


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════

# Backward-compatible alias used by some consumers
ScenarioBot = ScenarioTGBot

bot_instance = ScenarioTGBot()


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.cmd_start(update, context)

async def _status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.cmd_status(update, context)

async def _scenarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.cmd_scenarios(update, context)

async def _reload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.cmd_reload(update, context)

async def _escalate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.cmd_escalate(update, context)

async def _callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.handle_callback(update, context)

async def _text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.handle_text(update, context)


def main() -> int:
    if not bot_instance.token:
        print(
            "❌ TELEGRAM_BOT_TOKEN не задан.\n"
            "Получи токен у @BotFather и запусти:\n"
            "    TELEGRAM_BOT_TOKEN=xxx python freebuff_plugin_03/tgbot.py\n"
            "Или добавь TELEGRAM_BOT_TOKEN в .env файл."
        )
        return 1

    app = bot_instance.build_application()

    # Команды
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("status", _status))
    app.add_handler(CommandHandler("scenarios", _scenarios))
    app.add_handler(CommandHandler("reload", _reload))
    app.add_handler(CommandHandler("escalate", _escalate))

    # Inline callback
    app.add_handler(CallbackQueryHandler(_callback))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _text))

    logger.info("🤖 Freebuff Plugin TG Bot запущен")
    print("🤖 Freebuff Plugin TG Bot запущен. Нажми Ctrl+C для остановки.")

    return bot_instance.run_polling(app)


if __name__ == "__main__":
    sys.exit(main())
