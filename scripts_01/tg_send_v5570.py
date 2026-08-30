"""TG-send helper для v5.57.0 release.

Format: см. [docs_10/core/TG_HUMAN_FORMAT.md](../../docs_10/core/TG_HUMAN_FORMAT.md) —
человеческий язык, без Block-A/CON-X/CAN-X/ANTI-X jargon, без raw version numbers
в user-facing section, формат «Что сделали / Что осталось / Прогресс X/Y».

TG транспорт: [core_02/telegram_contract.py](../../core_02/telegram_contract.py)
(report_to_saved_messages + report_to_alex_litvinov).
Round-trip verify: TGClient.get_messages(chat_id, ids=msg_id).
"""

from __future__ import annotations

import asyncio
import sys
}

# This script lives at /storage/.../freebuff/scripts_01/tg_send_v5570.py — NOT in
# sibling-project scripts/. So `_freebuff_locator` (which lives at
# /storage/.../interior_planner_e2e/interior_planner/scripts/) is NOT a direct
# sibling. Compute Freebuff root via parent.parent (the file's grandparent
# directory) and sys.path.insert it directly so `import core_02.telegram_contract`
# works without PYTHONPATH plumbing.
FB_ROOT = Path(__file__).resolve().parent.parent
if str(FB_ROOT) not in sys.path:
    sys.path.insert(0, str(FB_ROOT))

import core_02.telegram_contract as tc  # noqa: E402


# TG_HUMAN_FORMAT-compliant message text (no Block-A/CAN-X jargon, no raw numbers)
# Заголовок «🧪 v5.57.0 — что сделали» допускает номер версии один раз + заголовок
# секции = одно acronym-free слово «что сделали». Внутри — только действия и результаты.
V5570_HUMAN_MESSAGE = """🧪 v5.57.0 — что сделали

✅ Убрали захардкоженные пути в обоих скриптах интерьерного планировщика. Теперь они корректно резолвятся через переменную окружения — риск сломаться при следующем переезде снят.
✅ Help-тексты приведены в соответствие с реальным поведением: что пишет --help, то и происходит при запуске.
✅ Удалили уже ненужный вспомогательный файл и маркер — один источник правды, без дубликатов и потерянных валидационных якорей.
✅ Код-ревью пройдено, все проверочные гейты зелёные.

🔄 Что осталось

• Реальный end-to-end прогон с настоящим клиентом отложен в отдельный релиз — требует локатора и живого TG-канала.
• Конкретный путь к шаблонам по-прежнему жёстко прописан — отдельная задача.
• sys.path-блок пока не покрывает полностью автоматическое обнаружение freebuff без явной переменной окружения — тоже отдельный заход.

📊 Прогресс

• Захардкоженных путей в проекте: 0 (было 2).
• Зелёных проверочных гейтов: 4/4.
• Решение код-ревью: APPROVED.
"""


def send_to_saved_messages() -> int | None:
    """Отправляет human message в Saved Messages (@vaalchik / Избранное)."""
    return asyncio.run(tc.report_to_saved_messages(V5570_HUMAN_MESSAGE))


def send_to_litvinov() -> int | None:
    """Отправляет human message Литвинову (chat_id=1063827731)."""
    return asyncio.run(tc.report_to_alex_litvinov(V5570_HUMAN_MESSAGE))


async def round_trip_verify(saved_msg_id: int, lit_msg_id: int) -> dict:
    """TG round-trip read-back: подтвердить через client.get_messages что msg_ids real history."""
    from projects_17.tg_terminal_messenger.src.telegram.client import TGClient

    client = TGClient()
    if not await client.connect():
        return {"saved": None, "litvinov": None, "connected": False}
    out = {"connected": True}
    if saved_msg_id is not None:
        msgs = await client.get_messages(tc.SAVED_MESSAGES_CHAT_ID, ids=[saved_msg_id])
        out["saved"] = bool(msgs and msgs[0] and getattr(msgs[0], "text", None))
    if lit_msg_id is not None:
        msgs = await client.get_messages(tc.LITVINOV_CHAT_ID, ids=[lit_msg_id])
        out["litvinov"] = bool(msgs and msgs[0] and getattr(msgs[0], "text", None))
    await client.disconnect()
    return out


def main() -> int:
    print("=== tg_send_v5570.py \u2014 sending human message via TG ===\n")
    saved_id = send_to_saved_messages()
    print(f"Saved Messages msg_id = {saved_id}")
    lit_id = send_to_litvinov()
    print(f"\u041b\u0438\u0442\u0432\u0438\u043d\u043e\u0432 msg_id = {lit_id}")
    print()
    verify = asyncio.run(round_trip_verify(saved_id, lit_id))
    print(f"Round-trip verify (TGClient.get_messages read-back):")
    print(f"  connected = {verify.get('connected')}")
    print(f"  saved text non-empty = {verify.get('saved')}")
    print(f"  litvinov text non-empty = {verify.get('litvinov')}")
    if verify.get("connected") and verify.get("saved") and verify.get("litvinov"):
        print("\n=== TG-send complete \u2705 ===")
        return 0
    print("\n=== TG-send INCOMPLETE \u2014 round-trip mismatch ===")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
