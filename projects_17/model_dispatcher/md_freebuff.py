"""md_freebuff.py — драйвер freebuff TUI (имитация действий человека, 081_19_model_dispatcher).

Запускает freebuff в tmux, ждёт стартового экрана, определяет доступную
мощную модель (через md_models), выбирает её стрелками ArrowDown ×N + Enter,
ждёт приглашения «Enter a coding task», отправляет промпт, мониторит
вылеты/таймер и корректно завершает или приостанавливает сессию.

Ключевые сценарии (081_19_model_dispatcher):
  - «смотрел, какая из мощных моделей доступна и выбирал по нисходящей»;
  - «контролировал вылеты и время» (рестарты + таймер сессии);
  - «сессия, ориентированная на час, не исчезает» (--continue + pause/resume).

Все tmux-операции инъектируемы (команды передаются функциями-параметрами)
для unit-тестов без реального tmux.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import md_models

# ── Маркеры экрана (сопоставимо с freebuff_plugin_03/monitor.sh) ──

SCREEN_START_MARKERS = ("recommended", "start coding", "choose a model", "select a model")
SCREEN_READY_MARKERS = ("enter a coding task", "coding task", "ask anything", "start coding")
SINGLE_INSTANCE_MARKERS = (
    "freebuff is already running",
    "only one freebuff instance is allowed",
    "take over",
)


def clean_tui(text: str) -> str:
    """Очищает дамп TUI от ANSI/управляющих последовательностей."""
    text = re.sub(r"\x1b\[[0-9;)*[a-zA-Z]", "", text)
    text = re.sub(r"\x1b\*)[^\x07]*\x07", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f)", "", text)
    return text


@dataclass
class SessionResult:
    """Результат сессии freebuff."""

    ok: bool
    status: str            # done | timeout | crashed | blocked | error
    model_used: str = ""
    output: str = ""
    error: str = ""
    attempts: int = 0
    duration_s: float = 0.0


# Типы команд (инъекция для тестов)
RunCmd = Callable[[List[str]], Any]
CapturePane = Callable[[str], str]
SendKeys = Callable[[str, str], None]
HasSession = Callable[[str], bool]


class FreebuffDriver:
    """Тонкий tmux-драйвер freebuff.

    Args:
        work_dir: рабочая директория (cwd сессии freebuff).
        binary_cmd: команда запуска freebuff (если пусто — из config).
        session_name: имя tmux-сессии (если пусто — авто UUID).
        timeout_s: таймер сессии (сек), по умолчанию 3600 (1 час).
        model_priority: список моделей из config (models.priority).
        unavailable_markers: маркеры недоступности моделей.
        max_restarts: сколько раз перезапускать при вылете.
        restart_delay_s: пауза между рестартами.
        startup_wait_s: сколько ждать стартового экрана/приглашения.
        poll_s: поллинг мониторинга.
        continue_resume: использовать `freebuff --continue` при возобновлении.
    """

    def __init__(
        self,
        work_dir: str | Path,
        binary_cmd: str = "",
        session_name: str = "",
        timeout_s: int = 3600,
        model_priority: Optional[List[Dict[str, Any]]] = None,
        unavailable_markers: Optional[List[str]] = None,
        max_restarts: int = 2,
        restart_delay_s: int = 10,
        startup_wait_s: int = 120,
        poll_s: int = 3,
        continue_resume: bool = True,
        resume: bool = False,
        run_cmd: Optional[RunCmd] = None,
        capture_pane: Optional[CapturePane] = None,
        send_keys: Optional[SendKeys] = None,
        has_session: Optional[HasSession] = None,
    ):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.binary_cmd = binary_cmd
        self.session_name = session_name or f"md_{uuid.uuid4().hex[:8]}"
        self.timeout_s = timeout_s
        self.model_priority = model_priority or []
        self.unavailable_markers = [str(m).lower() for m in (unavailable_markers or [])]
        self.max_restarts = max_restarts
        self.restart_delay_s = restart_delay_s
        self.startup_wait_s = startup_wait_s
        self.poll_s = poll_s
        self.continue_resume = continue_resume
        # True = возобновление существующей сессии (--continue в launch cmd);
        # False = свежий запуск (новая задача стартует с чистого контекста).
        self.resume = resume

        self._run_cmd = run_cmd or self._default_run_cmd
        self._capture = capture_pane or self._default_capture_pane
        self._send = send_keys or self._default_send_keys
        self._has_session = has_session or self._default_has_session

        self.selected_model: str = ""
        self._conversation_id: str = ""
        self._last_prompt: str = ""
        self.last_error: str = ""

    # ── Подключение к tmux ─────────────────────────────────────

    def _default_run_cmd(self, cmd: List[str]) -> Any:
        return subprocess.run(cmd, capture_output=True, timeout=10)

    def _default_capture_pane(self, session: str) -> str:
        r = subprocess.run(
            ["tmux", "capture-pane", "-t", session, "-p"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout or ""

    def _default_send_keys(self, session: str, keys: str) -> None:
        subprocess.run(
            ["tmux", "send-keys", "-t", session, keys, "Enter"],
            capture_output=True, timeout=5,
        )

    def _default_has_session(self, session: str) -> bool:
        r = subprocess.run(
            ["tmux", "has-session", "-t", session],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0

    # ── Запуск / остановка ─────────────────────────────────────

    def build_launch_cmd(self, cwd: Path) -> List[str]:
        """Строит команду запуска freebuff.

        Приоритет: бинарь из config (`binary_cmd`) → PATH (`freebuff`) →
        `--cwd <dir>`. Флаг `--continue` добавляется ТОЛЬКО при resume=True
        (возобновление существующей сессии), а не на свежих запусках —
        иначе новая задача прицепилась бы к предыдущему разговору.
        """
        if self.binary_cmd:
            parts = shlex.split(self.binary_cmd)
        else:
            parts = ["freebuff"]
        parts += ["--cwd", str(cwd)]
        if self.resume and self.continue_resume:
            parts += ["--continue"]
        return parts

    def start(self) -> bool:
        """Создаёт tmux-сессию с freebuff. Returns True если запущена.

        Проверяет returncode `tmux new-session`: неуспех (tmux нет, сессия
        с таким именем уже есть) → False + last_error (без hang в wait_for_screen).
        """
        cmd = self.build_launch_cmd(self.work_dir)
        shell_cmd = " ".join(shlex.quote(p) for p in cmd)
        tmux_new = ["tmux", "new-session", "-d", "-s", self.session_name, shell_cmd]
        try:
            r = self._run_cmd(tmux_new)
            rc = getattr(r, "returncode", 0)
            if rc is not None and rc != 0:
                self.last_error = f"tmux new-session rc={rc}"
                return False
            return True
        except Exception as e:
            self.last_error = f"tmux new-session failed: {e}"
            return False

    def stop(self) -> None:
        """Убивает tmux-сессию (если жива)."""
        if self._has_session(self.session_name):
            self._run_cmd(["tmux", "kill-session", "-t", self.session_name])

    def is_alive(self) -> bool:
        return self._has_session(self.session_name)

    def capture(self) -> str:
        return clean_tui(self._capture(self.session_name))

    # ── Сценарий «имитация человека» ───────────────────────────

    def wait_for_screen(self, timeout_s: Optional[int] = None) -> str:
        """Ждёт появления стартового экрана/приглашения. Возвращает дамп.

        Маркеры готовности берутся из SCREEN_START_MARKERS /
        SCREEN_READY_MARKERS. Возвращает последний дамп даже при таймауте.
        """
        deadline = time.time() + (timeout_s or self.startup_wait_s)
        last = ""
        while time.time() < deadline:
            if not self.is_alive():
                break
            last = self.capture()
            low = last.lower()
            if any(m in low for m in SCREEN_READY_MARKERS):
                return last
            if any(m in low for m in SCREEN_START_MARKERS):
                time.sleep(1.0)
                continue
            time.sleep(self.poll_s)
        return last

    def select_best_model(self, screen_text: str) -> md_models.ModelSelection:
        """Анализирует экран и выбирает модель по убыванию мощности.

        Returns:
            ModelSelection. Выполняет навигацию ArrowDown ×position + Enter,
            если позиция > 0 (0 = рекомендованная, Enter достаточно).

        NOTE: position — индекс среди РАСПОЗНАННЫХ строк моделей, а не
        абсолютная строка TUI. Если список моделей имеет пустые строки между
        пунктами, количество Down может отличаться от физического смещения.
        Настраивается через keywords/markers в config.yaml под реальный layout.
        """
        entries = md_models.parse_screen(
            screen_text, self.model_priority, self.unavailable_markers
        )
        sel = md_models.pick_model(entries, self.model_priority)
        self.selected_model = sel.name
        if sel.position > 0:
            for _ in range(sel.position):
                self._send(self.session_name, "Down")
        self._send(self.session_name, "Enter")
        return sel

    def send_prompt(self, prompt: str) -> None:
        """Отправляет промпт в поле ввода freebuff (send-keys + Enter).

        Запоминает промпт в `_last_prompt` — после рестарта (вылета) мониторинг
        переотправляет его в свежий инстанс (иначе рестарт был бы бесполезен:
        freebuff стартует на стартовом экране без задачи).
        """
        self._last_prompt = prompt
        self._send(self.session_name, prompt)

    # ── Мониторинг ─────────────────────────────────────────────

    def monitor(
        self,
        result_marker: str = ".freebuff_result",
        baseline_mtime: Optional[int] = None,
    ) -> SessionResult:
        """Мониторит сессию до завершения/таймаута/вылета.

        Args:
            result_marker: имя файла-маркера результата (в work_dir).
            baseline_mtime: mtime_ns «до» запуска — защита от стейл-файла
                (уже существующий .freebuff_result в воркспейсе дал бы
                ложный done). Принимаем маркер только если mtime > baseline.

        Returns:
            SessionResult. Статусы:
              - done    — маркер результата появился (mtime > baseline);
              - timeout — таймер истёк, tmux-сессия СОХРАНЕНА (--continue);
              - crashed — вылет tmux, рестарты исчерпаны.
        """
        start = time.time()
        deadline = start + self.timeout_s
        attempts = 0
        marker = self.work_dir / result_marker

        while time.time() < deadline:
            # Результат появился (и он НОВЫЙ)?
            if marker.exists():
                try:
                    mtime = marker.stat().st_mtime_ns
                except OSError:
                    mtime = -1
                if baseline_mtime is None or mtime > baseline_mtime:
                    return SessionResult(
                        ok=True, status="done",
                        model_used=self.selected_model,
                        output=self.capture(),
                        duration_s=round(time.time() - start, 1),
                    )
            if not self.is_alive():
                attempts += 1
                if attempts > self.max_restarts:
                    return SessionResult(
                        ok=False, status="crashed",
                        model_used=self.selected_model,
                        output=self.capture(),
                        error=f"freebuff вылетел {attempts} раз",
                        attempts=attempts,
                        duration_s=round(time.time() - start, 1),
                    )
                time.sleep(self.restart_delay_s)
                if not self.start():
                    return SessionResult(
                        ok=False, status="crashed",
                        error="не удалось перезапустить tmux-сессию",
                        attempts=attempts,
                        duration_s=round(time.time() - start, 1),
                    )
                # Рестарт: свежий инстанс на стартовом экране → повторяем выбор
                # модели (для fresh-задач) и переотправляем промпт (иначе рестарт
                # бесполезен). Для resume-задач модель уже выбрана в сессии.
                if not self.resume:
                    screen = self.wait_for_screen(timeout_s=self.startup_wait_s)
                    self.select_best_model(screen)
                if self._last_prompt:
                    self.send_prompt(self._last_prompt)
                continue
            time.sleep(self.poll_s)

        # Таймаут: сессию НЕ убиваем (сохраняем контекст).
        return SessionResult(
            ok=False, status="timeout",
            model_used=self.selected_model,
            output=self.capture(),
            error=f"timeout after {self.timeout_s}s (сессия сохранена для --continue)",
            attempts=attempts,
            duration_s=round(time.time() - start, 1),
        )

    # ── Сессии / контекст ──────────────────────────────────────

    def save_context(self, task_id: str) -> Path:
        """Сохраняет контекст сессии (имя tmux + модель) в файл состояния.

        Позволяет возобновить «часовую сессию» позже (--continue).
        """
        state_dir = self.work_dir / ".md_state"
        state_dir.mkdir(parents=True, exist_ok=True)
        state = state_dir / f"{task_id}.json"
        import json
        data = {
            "tmux_session": self.session_name,
            "model": self.selected_model,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "conversation_id": self._conversation_id,
        }
        state.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return state
