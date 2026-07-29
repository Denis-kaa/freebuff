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
  TELEGRAM_BOT_TOKEN=xxx python freebuff_plugin/tgbot.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
***REMOVED***
from typing import Any

***REMOVED***
import time as _time

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
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

from freebuff_plugin.scenario_engine import ScenarioEngine

# ── Логирование ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("freebuff.tgbot")

# ── Токен ────────────────────────────────────────────────────

# Загрузка .env если есть
_env_path = FREEBUFF_ROOT / ".env"
if _env_path.exists():
    _content = _env_path.read_text(encoding="utf-8")
    for _line in _content.splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _val = _line.partition("=")
        os.environ.setdefault(_key.strip(), _val.strip().strip("'\""))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# ── Callback data префиксы ───────────────────────────────────

CALLBACK_PREFIXES = {
    "CAT": "sc_cat_",       # выбор категории
    "SC": "sc_sc_",         # выбор сценария
    "APPLY": "sc_apply_",   # применить сценарий
    "BACK_CAT": "sc_back_cat",   # назад к категориям
    "BACK_SC": "sc_back_sc_",    # назад к списку сценариев в категории
    "VARS": "sc_vars_",     # запросить переменные
***REMOVED***

# ═══════════════════════════════════════════════════════════════
# Bot
# ═══════════════════════════════════════════════════════════════

class ScenarioTGBot:
    """Telegram бот для навигации и применения сценариев."""

    def __init__(self):
        self.engine = ScenarioEngine()
        # Хранилище временных состояний: {chat_id: {slug, step, timestamp***REMOVED******REMOVED***
        self._states: dict[int, dict[str, Any***REMOVED******REMOVED*** = {***REMOVED***
        self._max_states = 1000  # макс. записей в _states
        self._state_ttl = 600   # 10 минут — время жизни состояния

    # ── Очистка устаревших состояний ────────────────────────

    def _prune_states(self) -> None:
        """Удаляет устаревшие состояния (старше _state_ttl секунд)."""
        now = _time.time()
        stale = [
            cid for cid, st in self._states.items()
            if _time.time() - st.get("timestamp", 0) > self._state_ttl
        ***REMOVED***
        for cid in stale:
            del self._states[cid***REMOVED***
        # Если всё ещё больше лимита — удаляем самые старые
        if len(self._states) > self._max_states:
            sorted_cids = sorted(
                self._states.keys(),
                key=lambda cid: self._states[cid***REMOVED***.get("timestamp", 0),
            )
            excess = len(self._states) - self._max_states
            for cid in sorted_cids[:excess***REMOVED***:
                del self._states[cid***REMOVED***

    def _set_state(self, chat_id: int, data: dict[str, Any***REMOVED***) -> None:
        """Устанавливает состояние с временем жизни."""
        self._prune_states()
        data["timestamp"***REMOVED*** = _time.time()
        self._states[chat_id***REMOVED*** = data

    def _get_state(self, chat_id: int) -> dict[str, Any***REMOVED*** | None:
        """Возвращает состояние, если оно не устарело."""
        state = self._states.get(chat_id)
        if state is None:
            return None
        if _time.time() - state.get("timestamp", 0) > self._state_ttl:
            del self._states[chat_id***REMOVED***
            return None
        return state

    def _del_state(self, chat_id: int) -> None:
        """Удаляет состояние."""
        self._states.pop(chat_id, None)

    # ── Вспомогательные методы ──────────────────────────────

    def _get_categories(self) -> list[str***REMOVED***:
        """Возвращает список уникальных категорий сценариев."""
        scenarios = self.engine.list_scenarios()
        cats: set[str***REMOVED*** = set()
        for s in scenarios:
            if s.get("category"):
                cats.add(s["category"***REMOVED***)
        return sorted(cats)

    def _scenarios_by_category(self, category: str) -> list[dict[str, Any***REMOVED******REMOVED***:
        """Сценарии в категории."""
        return self.engine.list_scenarios(category=category)

    def _format_scenario_list(self, scenarios: list[dict[str, Any***REMOVED******REMOVED***, show_category: bool = True) -> str:
        """Форматирует список сценариев для сообщения."""
        if not scenarios:
            return "😕 Нет сценариев."
        
        lines = [***REMOVED***
        for s in scenarios:
            tags = f"[{', '.join(s.get('tags', [***REMOVED***))***REMOVED******REMOVED***" if s.get('tags') else ""
            cat = f" [{s['category'***REMOVED******REMOVED******REMOVED***" if show_category and s.get('category') else ""
            lines.append(
                f"• *{s['title'***REMOVED******REMOVED****{cat***REMOVED***\n"
                f"  `{s['slug'***REMOVED******REMOVED***` — {s.get('description', '')[:100***REMOVED******REMOVED***"
            )
        return "\n\n".join(lines)

    def _format_scenario_detail(self, scenario: dict[str, Any***REMOVED***) -> str:
        """Форматирует детали одного сценария."""
        tags = ", ".join(scenario.get("tags", [***REMOVED***))
        return (
            f"📋 *{scenario['title'***REMOVED******REMOVED****\n\n"
            f"🔖 Slug: `{scenario['slug'***REMOVED******REMOVED***`\n"
            f"📂 Категория: {scenario.get('category', '—')***REMOVED***\n"
            f"⚙️ Сложность: {scenario.get('complexity', '—')***REMOVED***\n"
            f"🏷️ Теги: {tags or '—'***REMOVED***\n\n"
            f"📝 *Описание:*\n{scenario.get('description', '—')[:300***REMOVED******REMOVED***"
        )

    # ── Inline клавиатуры ───────────────────────────────────

    def _categories_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура выбора категории."""
        buttons = [***REMOVED***
        for cat in self._get_categories():
            scenarios = self._scenarios_by_category(cat)
            emoji = {
                "freelancing": "💼",
                "agent": "🤖",
                "templates": "📝",
            ***REMOVED***.get(cat, "📁")
            count = len(scenarios)
            buttons.append([
                InlineKeyboardButton(
                    f"{emoji***REMOVED*** {cat.capitalize()***REMOVED*** ({count***REMOVED***)",
                    callback_data=f"{CALLBACK_PREFIXES['CAT'***REMOVED******REMOVED***{cat***REMOVED***",
                )
            ***REMOVED***)
        buttons.append([
            InlineKeyboardButton("📋 Все сценарии", callback_data=f"{CALLBACK_PREFIXES['CAT'***REMOVED******REMOVED***all"),
        ***REMOVED***)
        buttons.append([
            InlineKeyboardButton("🔍 Поиск", switch_inline_query_current_chat="/scenarios search "),
        ***REMOVED***)
        return InlineKeyboardMarkup(buttons)

    def _scenarios_keyboard(self, category: str) -> InlineKeyboardMarkup:
        """Клавиатура со сценариями в категории."""
        if category == "all":
            scenarios = self.engine.list_scenarios()
        else:
            scenarios = self._scenarios_by_category(category)
        
        buttons = [***REMOVED***
        for s in scenarios:
            buttons.append([
                InlineKeyboardButton(
                    f"{s['title'***REMOVED***[:40***REMOVED******REMOVED***",
                    callback_data=f"{CALLBACK_PREFIXES['SC'***REMOVED******REMOVED***{s['slug'***REMOVED******REMOVED***",
                )
            ***REMOVED***)
        buttons.append([
            InlineKeyboardButton("← Назад к категориям", callback_data=CALLBACK_PREFIXES["BACK_CAT"***REMOVED***),
        ***REMOVED***)
        return InlineKeyboardMarkup(buttons)

    def _scenario_detail_keyboard(self, slug: str, category: str) -> InlineKeyboardMarkup:
        """Клавиатура действий для сценария."""
        scenario = self.engine.get_scenario(slug)
        buttons = [***REMOVED***
        if scenario and scenario.prompt_template:
            buttons.append([
                InlineKeyboardButton(
                    "🚀 Применить",
                    callback_data=f"{CALLBACK_PREFIXES['APPLY'***REMOVED******REMOVED***{slug***REMOVED***",
                )
            ***REMOVED***)
        buttons.append([
            InlineKeyboardButton("← Назад", callback_data=f"{CALLBACK_PREFIXES['BACK_SC'***REMOVED******REMOVED***{category***REMOVED***"),
        ***REMOVED***)
        return InlineKeyboardMarkup(buttons)

    def _variables_keyboard(self, slug: str) -> InlineKeyboardMarkup:
        """Клавиатура для ввода переменных."""
        buttons = [
            [
                InlineKeyboardButton("✅ Без переменных", callback_data=f"{CALLBACK_PREFIXES['VARS'***REMOVED******REMOVED***{slug***REMOVED***"),
            ***REMOVED***,
            [
                InlineKeyboardButton("← Назад", callback_data=f"{CALLBACK_PREFIXES['SC'***REMOVED******REMOVED***{slug***REMOVED***"),
            ***REMOVED***,
        ***REMOVED***
        return InlineKeyboardMarkup(buttons)

    def _home_keyboard(self) -> InlineKeyboardMarkup:
        """Клавиатура главного меню."""
        buttons = [
            [InlineKeyboardButton("📋 Сценарии", callback_data=CALLBACK_PREFIXES["BACK_CAT"***REMOVED***)***REMOVED***,
            [
                InlineKeyboardButton("💬 Статус", callback_data="sc_status"),
                InlineKeyboardButton("❓ Помощь", callback_data="sc_help"),
            ***REMOVED***,
        ***REMOVED***
        return InlineKeyboardMarkup(buttons)

    # ── Получение шаблона переменных ─────────────────────────

    def _extract_variable_names(self, prompt_template: str) -> list[str***REMOVED***:
        """Извлекает имена переменных из {placeholders***REMOVED***."""
        return list(set(re.findall(r"\{(\w+)\***REMOVED***", prompt_template)))

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
            f"📚 Всего сценариев: {len(self.engine.list_scenarios())***REMOVED***"
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
        cat_lines = "\n".join(f"  • {c***REMOVED***: {len(self._scenarios_by_category(c))***REMOVED***" for c in cats)
        text = (
            "📊 *Freebuff Plugin Status*\n\n"
            f"📚 Сценариев: {len(scenarios)***REMOVED***\n"
            f"📂 Категории:\n{cat_lines***REMOVED***\n\n"
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
        args = context.args or [***REMOVED***

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

        subcommand = args[0***REMOVED***.lower()

        if subcommand == "list":
            await self._handle_list(update, args[1:***REMOVED***, context)
        elif subcommand == "apply":
            await self._handle_apply(update, args[1:***REMOVED***, context)
        elif subcommand == "search":
            await self._handle_search(update, args[1:***REMOVED***, context)
        else:
            await update.effective_message.reply_text(
                f"Неизвестная подкоманда: `{subcommand***REMOVED***`\n"
                "Доступно: `list`, `apply`, `search`\n"
                "Пример: `/scenarios list`",
                parse_mode="Markdown",
            )

    # ── Подкоманды /scenarios ──

    async def _handle_list(self, update: Update, args: list[str***REMOVED***, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка /scenarios list [category***REMOVED***."""
        category = " ".join(args).strip() if args else None

        if category:
            scenarios = self.engine.list_scenarios(category=category)
            if not scenarios:
                await update.effective_message.reply_text(
                    f"😕 В категории «{category***REMOVED***» нет сценариев.\n"
                    f"Доступные категории: {', '.join(self._get_categories())***REMOVED***",
                )
                return
            text = f"📋 *Сценарии: {category***REMOVED****\n\n" + self._format_scenario_list(scenarios, show_category=False)
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

    async def _handle_apply(self, update: Update, args: list[str***REMOVED***, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработка /scenarios apply <slug> [var=value ...***REMOVED***."""
        if not args:
            await update.effective_message.reply_text(
                "Укажи slug сценария:\n"
                "`/scenarios apply freelance_parser`\n"
                "`/scenarios apply freelance_parser URL=https://...`",
                parse_mode="Markdown",
            )
            return

        slug = args[0***REMOVED***
        scenario = self.engine.get_scenario(slug)
        if not scenario:
            await update.effective_message.reply_text(
                f"😕 Сценарий `{slug***REMOVED***` не найден.\n"
                f"Доступные: {', '.join(s.slug for s in self.engine._scenarios.values())***REMOVED***",
                parse_mode="Markdown",
            )
            return

        # Извлекаем переменные из аргументов
        variables: dict[str, str***REMOVED*** = {***REMOVED***
        for arg in args[1:***REMOVED***:
            if "=" in arg:
                k, _, v = arg.partition("=")
                variables[k.strip()***REMOVED*** = v.strip()

        # Если есть неподставленные переменные — показываем список
        var_names = self._extract_variable_names(scenario.prompt_template)
        missing = [v for v in var_names if v not in variables***REMOVED***

        if missing and not variables:
            var_list = "\n".join(f"  • `{v***REMOVED***`" for v in missing)
            text = (
                f"📋 *{scenario.title***REMOVED****\n\n"
                f"🔖 Slug: `{scenario.slug***REMOVED***`\n\n"
                f"Для применения укажи переменные:\n{var_list***REMOVED***\n\n"
                f"Пример:\n"
                f"`/scenarios apply {scenario.slug***REMOVED*** {'=значение '.join(missing)***REMOVED***={'значение' * bool(missing)***REMOVED***`"
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
            await update.effective_message.reply_text(f"❌ {result['error'***REMOVED******REMOVED***")
            return

        prompt = result["prompt"***REMOVED***
        await self._send_prompt(update, prompt, slug, result["title"***REMOVED***)

    async def _handle_search(self, update: Update, args: list[str***REMOVED***, context: ContextTypes.DEFAULT_TYPE) -> None:
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
                f"😕 По запросу «{query***REMOVED***» ничего не найдено."
            )
            return

        text = f"🔍 *Результаты поиска: «{query***REMOVED***»* ({len(results)***REMOVED***)\n\n"
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
                "text": f"✅ *Сценарий применён*\n\n```\n{prompt***REMOVED***\n```",
                "parse_mode": "Markdown",
            ***REMOVED***
            if is_edit:
                await reply_or_edit.edit_message_text(**kwargs)
            else:
                await reply_or_edit.reply_text(**kwargs)
        else:
            text_preview = (
                f"✅ *Сценарий применён*\n📏 Промт ({len(prompt)***REMOVED*** символов) — "
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
                    filename=f"{slug***REMOVED***_prompt.md",
                    caption=f"📋 {title***REMOVED*** — готовый промт",
                )
            else:
                await reply_or_edit.reply_document(
                    document=prompt.encode("utf-8"),
                    filename=f"{slug***REMOVED***_prompt.md",
                    caption=f"📋 {title***REMOVED*** — готовый промт",
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
            f"🔄 Сценарии перезагружены. Загружено: {count***REMOVED***",
        )

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
                    variables = {***REMOVED***
                    for line in text.split("\n"):
                        line = line.strip()
                        if "=" in line:
                            k, _, v = line.partition("=")
                            variables[k.strip()***REMOVED*** = v.strip()

                # Проверка на команду "готово" — применить без переменных
                if text.strip().lower() in ("готово", "да", "yes", "done", "apply"):
                    variables = {***REMOVED***
                elif not variables:
                    # Применяем без переменных
                    variables = {***REMOVED***

                slug = state["slug"***REMOVED***
                result = self.engine.apply_scenario(slug, variables)
                self._del_state(chat_id)

                if "error" in result:
                    await update.effective_message.reply_text(f"❌ {result['error'***REMOVED******REMOVED***")
                    return

                await self._send_prompt(
                    update, result["prompt"***REMOVED***, slug, result["title"***REMOVED***
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
            cat_lines = "\n".join(f"  • {c***REMOVED***: {len(self._scenarios_by_category(c))***REMOVED***" for c in cats)
            text = (
                "📊 *Freebuff Plugin Status*\n\n"
                f"📚 Сценариев: {len(scenarios)***REMOVED***\n"
                f"📂 Категории:\n{cat_lines***REMOVED***"
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
        elif data.startswith(CALLBACK_PREFIXES["CAT"***REMOVED***):
            category = data[len(CALLBACK_PREFIXES["CAT"***REMOVED***):***REMOVED***
            if category == "all":
                scenarios = self.engine.list_scenarios()
                cat_display = "все"
            else:
                scenarios = self._scenarios_by_category(category)
                cat_display = category

            if not scenarios:
                await query.edit_message_text(
                    f"😕 В категории «{cat_display***REMOVED***» нет сценариев.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("← Назад", callback_data=CALLBACK_PREFIXES["BACK_CAT"***REMOVED***),
                    ***REMOVED******REMOVED***),
                )
                return

            text = f"📋 *Сценарии: {cat_display***REMOVED****\n\n" + self._format_scenario_list(scenarios, show_category=False)
            await query.edit_message_text(
                text,
                reply_markup=self._scenarios_keyboard(category),
                parse_mode="Markdown",
            )

        # ── Выбор сценария → детали ──
        elif data.startswith(CALLBACK_PREFIXES["SC"***REMOVED***):
            slug = data[len(CALLBACK_PREFIXES["SC"***REMOVED***):***REMOVED***
            scenario = self.engine.get_scenario(slug)
            if not scenario:
                await query.edit_message_text(f"😕 Сценарий {slug***REMOVED*** не найден.")
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
        elif data.startswith(CALLBACK_PREFIXES["APPLY"***REMOVED***):
            slug = data[len(CALLBACK_PREFIXES["APPLY"***REMOVED***):***REMOVED***
            scenario = self.engine.get_scenario(slug)
            if not scenario:
                await query.edit_message_text(f"😕 Сценарий {slug***REMOVED*** не найден.")
                return

            # Извлекаем переменные из шаблона
            var_names = self._extract_variable_names(scenario.prompt_template)
            if not var_names:
                # Нет переменных — применяем сразу
                result = self.engine.apply_scenario(slug)
                await self._send_prompt_result(
                    query, result["prompt"***REMOVED***, slug, scenario.title, is_edit=True
                )
            else:
                # Просим ввести переменные
                self._set_state(chat_id, {"slug": slug, "step": "wait_vars"***REMOVED***)
                
                var_list = "\n".join(f"  • `{v***REMOVED***` = значение" for v in var_names)
                text = (
                    f"✏️ *Введи переменные для «{scenario.title***REMOVED***»*\n\n"
                    f"Необходимые переменные:\n{var_list***REMOVED***\n\n"
                    f"Отправь в формате:\n"
                    f"`ключ1=значение1`\n"
                    f"`ключ2=значение2`\n\n"
                    f"Или отправь `готово` чтобы применить без переменных."
                )
                await query.edit_message_text(
                    text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("✅ Применить без переменных", callback_data=f"{CALLBACK_PREFIXES['VARS'***REMOVED******REMOVED***{slug***REMOVED***"),
                    ***REMOVED***, [
                        InlineKeyboardButton("← Назад", callback_data=CALLBACK_PREFIXES["BACK_SC"***REMOVED*** + scenario.category),
                    ***REMOVED******REMOVED***),
                    parse_mode="Markdown",
                )

        # ── Применить без/с переменными ──
        elif data.startswith(CALLBACK_PREFIXES["VARS"***REMOVED***):
            slug = data[len(CALLBACK_PREFIXES["VARS"***REMOVED***):***REMOVED***
            scenario = self.engine.get_scenario(slug)
            if not scenario:
                await query.edit_message_text(f"😕 Сценарий {slug***REMOVED*** не найден.")
                return

            result = self.engine.apply_scenario(slug)
            # Очищаем состояние
            self._del_state(chat_id)
            await self._send_prompt_result(
                query, result["prompt"***REMOVED***, slug, scenario.title, is_edit=True
            )

        # ── Назад к категориям ──
        elif data == CALLBACK_PREFIXES["BACK_CAT"***REMOVED***:
            text = "📋 *Сценарии разработки*\n\nВыбери категорию:"
            await query.edit_message_text(
                text,
                reply_markup=self._categories_keyboard(),
                parse_mode="Markdown",
            )

        # ── Назад к списку сценариев в категории ──
        elif data.startswith(CALLBACK_PREFIXES["BACK_SC"***REMOVED***):
            category = data[len(CALLBACK_PREFIXES["BACK_SC"***REMOVED***):***REMOVED***
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
                text = f"📋 *Сценарии: {category***REMOVED****\n\n" + self._format_scenario_list(scenarios, show_category=False)
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

async def _callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.handle_callback(update, context)

async def _text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await bot_instance.handle_text(update, context)


def main() -> int:
    if not TELEGRAM_BOT_TOKEN:
        print(
            "❌ TELEGRAM_BOT_TOKEN не задан.\n"
            "Получи токен у @BotFather и запусти:\n"
            "    TELEGRAM_BOT_TOKEN=xxx python freebuff_plugin/tgbot.py\n"
            "Или добавь TELEGRAM_BOT_TOKEN в .env файл."
        )
        return 1

    import asyncio

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # Команды
    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("status", _status))
    app.add_handler(CommandHandler("scenarios", _scenarios))
    app.add_handler(CommandHandler("reload", _reload))

    # Inline callback
    app.add_handler(CallbackQueryHandler(_callback))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _text))

    logger.info("🤖 Freebuff Plugin TG Bot запущен")
    print("🤖 Freebuff Plugin TG Bot запущен. Нажми Ctrl+C для остановки.")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as exc:
        logger.exception("Bot polling failed")
        print(f"❌ Bot polling failed: {exc***REMOVED***", file=sys.stderr)
        return 1
    finally:
        try:
            loop.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
