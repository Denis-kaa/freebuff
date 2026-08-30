"""
Freebuff Plugin — Intent Detection Router.

Определяет, какой "исполнитель" нужен для запроса:

  1. local_qwen   — простые запросы (приветствия, статус, вопросы)
     Использует Qwen 2.5 0.5B через llama.cpp
  2. freebuff     — сложные задачи (код, архитектура, инструменты)
     Перенаправляет в Codebuff CLI через proot

Логика принятия решения:
  - Keyword scoring по категориям (как phone-agent/router.py)
  - Если уверенность > порога → решение
  - Если неуверен → freebuff (failover на мощного агента)

Использование:
    from freebuff_plugin_03.router import IntentRouter
    router = IntentRouter()
    result = router.route("напиши парсер JSON")
    # → {"target": "freebuff", "confidence": 0.85, "reason": "code keywords"}
"""

from __future__ import annotations

import os
}
import subprocess
import sys
}
from typing import Any

from freebuff_plugin_03.config import (
    FREEBUFF_BINARY,
    QWEN_MODEL_0_5B,
    LLAMA_CLI,
    INTENT_KEYWORDS,
)


# ═══════════════════════════════════════════════════════════════
# Intent Detection
# ═══════════════════════════════════════════════════════════════

# Паттерны для определения намерения (расширенные)
PATTERNS: dict[str, list[str]] = {
    # → Локально (Qwen 0.5B)
    "local_greeting": [
        r"^(привет|здравствуй|хай|хелло|hello|hi|hey|даров|здарова)",
        r"(как дела|как ты|как жизнь|чё как)",
        r"(спасибо|благодарю|ок|ok|ладно|понял|принял)",
        r"(пока|до свидания|увидимся|bye|goodbye)",
    ],
    "local_status": [
        r"(статус|состояние|health|здоровье)",
        r"(батарея|батарейка|заряд|battery)",
        r"(время|дата|date|time)",
        r"(погода|weather|температура)",
        r"(который час)",
    ],
    "local_simple_qa": [
        r"^(что такое|кто такой|что значит|what is|who is)",
        r"(напомни|помнишь|что я просил)",
        r"^(да|нет|не знаю|может быть)",
    ],

    # → Freebuff (сложные задачи)
    "freebuff_code": [
        r"(напиши|создай|напиcать|реализуй|implement|write|create)",
        r"(код|функци[юя]|класс|модуль|парсер|скрипт)",
        r"(рефактори|refactor|перепиши|переделай|исправь)",
        r"(тест|test|pytest|unittest|проверк[аи])",
        r"(тип[ы]|type|mypy|аннотаци[юя])",
    ],
    "freebuff_architecture": [
        r"(архитектур[ау]|спроектируй|design|спроектировать)",
        r"(схем[ау]|диаграмм[ау]|дизайн)",
        r"(баз[аы] данных|sqlite|postgres|бд|database)",
        r"(api|rest|graphql|grpc|эндпоинт)",
    ],
    "freebuff_tools": [
        r"(git|коммит|commit|пуш|push|ветк[ау]|branch|merge)",
        r"(миграци[юя]|migration|alembic)",
        r"(докер|docker|контейнер|deploy|деплой)",
        r"(установ|install|npm|pip|apt|пакет)",
    ],
    "freebuff_investigation": [
        r"(найди|поищи|найти|find|grep|search|lookup)",
        r"(баг|bug|ошибк[ау]|ошибки|логи|logs|debug)",
        r"(почем[уу]|отчего|зачем|как исправить|как починить)",
    ],
}

# Confidence thresholds
LOCAL_THRESHOLD = 0.6    # если уверенность > 60% → Qwen
FREEBUFF_THRESHOLD = 0.4  # если уверенность > 40% → freebuff


def _score_text(text: str, pattern_list: list[str]) -> float:
    """Считает совпадения текста со списком regex."""
    text_lower = text.lower()
    score = 0.0
    for pattern in pattern_list:
        match = re.search(pattern, text_lower)
        if match:
            # Длина совпадения / длину текста = вес
            matched_len = len(match.group())
            score += matched_len / max(len(text_lower), 1)
    return min(score, 1.0)


# ═══════════════════════════════════════════════════════════════
# Локальная Qwen 0.5B
# ═══════════════════════════════════════════════════════════════

QWEEN_SYSTEM_PROMPT = """Ты — локальный AI-ассистент, работающий на устройстве.
Твои возможности ограничены: ты отвечаешь на простые вопросы (приветствия, статус, время).
Если запрос сложный (код, архитектура, инструменты) — скажи "нужен freebuff" и опиши задачу кратко.

Будь краток. Отвечай на русском."""


def _call_qwen_local(prompt: str) -> str:
    """
    Запускает Qwen 2.5 0.5B через llama.cpp и возвращает ответ.
    """
    if not QWEN_MODEL_0_5B.exists():
        return "[Qwen 0.5B не найден — используй freebuff]"

    full_prompt = f"{QWEEN_SYSTEM_PROMPT}\n\nПользователь: {prompt}\nАссистент:"

    try:
        result = subprocess.run(
            [LLAMA_CLI, "-m", str(QWEN_MODEL_0_5B),
             "-p", full_prompt,
             "-n", "256",
             "-t", "2",
             "--no-display-prompt"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        # Очищаем ответ от лишнего
        if not output:
            output = result.stderr.strip()
        return output[:500] if output else "[Qwen не ответил]"

    except FileNotFoundError:
        return f"[llama-cli не найден. Установи: pkg install llama.cpp]"
    except subprocess.TimeoutExpired:
        return "[Qwen: таймаут]"
    except Exception as e:
        return f"[Qwen: {e}]"


# ═══════════════════════════════════════════════════════════════
# Router
# ═══════════════════════════════════════════════════════════════

class IntentRouter:
    """
    Роутер запросов: определяет, кому направить — Qwen 0.5B или freebuff.

    Использование:
        router = IntentRouter()
        decision = router.route("напиши парсер")
        # → {"target": "freebuff", "confidence": 0.85}

        answer = router.local_response("привет")
        # → "Привет! Чем могу помочь?"
    """

    def __init__(self):
        self.freebuff_binary = FREEBUFF_BINARY

    def route(self, text: str) -> dict[str, Any]:
        """
        Принимает решение: local_qwen или freebuff.

        Returns:
            dict:
                target: "local_qwen" | "freebuff"
                confidence: float 0-1
                reason: str
                scores: dict[str, float]
        """
        scores: dict[str, float] = {}

        # Считаем скоры по группам
        for group, patterns in PATTERNS.items():
            scores[group] = _score_text(text, patterns)

        # Суммарные скоры
        local_score = max(
            scores.get("local_greeting", 0),
            scores.get("local_status", 0),
            scores.get("local_simple_qa", 0),
        )
        freebuff_score = max(
            scores.get("freebuff_code", 0),
            scores.get("freebuff_architecture", 0),
            scores.get("freebuff_tools", 0),
            scores.get("freebuff_investigation", 0),
        )

        # Решение
        if local_score > LOCAL_THRESHOLD and local_score > freebuff_score:
            return {
                "target": "local_qwen",
                "confidence": round(local_score, 2),
                "reason": f"local score {local_score:.2f} > {LOCAL_THRESHOLD}",
                "scores": scores,
            }
        elif freebuff_score > FREEBUFF_THRESHOLD:
            return {
                "target": "freebuff",
                "confidence": round(freebuff_score, 2),
                "reason": f"freebuff score {freebuff_score:.2f} > {FREEBUFF_THRESHOLD}",
                "scores": scores,
            }
        else:
            # Неуверен → freebuff (failover)
            return {
                "target": "freebuff",
                "confidence": round(freebuff_score, 2),
                "reason": f"uncertain (local={local_score:.2f}, freebuff={freebuff_score:.2f}), failover to freebuff",
                "scores": scores,
            }

    def local_response(self, prompt: str) -> str:
        """Отвечает через Qwen 0.5B."""
        return _call_qwen_local(prompt)


# ═══════════════════════════════════════════════════════════════
# CLI тест
# ═══════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Intent Router CLI")
    parser.add_argument("query", nargs="?", help="Запрос для теста")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Интерактивный режим")

    args = parser.parse_args()
    router = IntentRouter()

    if args.interactive:
        print("Intent Router — интерактивный режим (Ctrl+C для выхода)")
        print()
        while True:
            try:
                q = input(">>> ")
                if not q:
                    continue
                decision = router.route(q)
                print(f"  → {decision['target']} (conf={decision['confidence']})")
                print(f"  → {decision['reason']}")
                if decision['target'] == 'local_qwen':
                    print(f"  → {router.local_response(q)}")
                print()
            except KeyboardInterrupt:
                print("\nbye")
                break
    elif args.query:
        decision = router.route(args.query)
        print(f"Query: {args.query}")
        print(f"Target: {decision['target']}")
        print(f"Confidence: {decision['confidence']}")
        print(f"Reason: {decision['reason']}")
        print(f"Scores: {decision['scores']}")

        if decision['target'] == 'local_qwen':
            print(f"\nLocal response: {router.local_response(args.query)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
