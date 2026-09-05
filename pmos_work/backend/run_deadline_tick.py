"""Run one deadline automation tick and exit."""
import asyncio

from app.database import SessionLocal
from app.scheduler import run_deadline_tick


async def main() -> None:
    async with SessionLocal() as db:
        emitted = await run_deadline_tick(db)
        print(f"deadline tick: emitted={emitted}")


if __name__ == "__main__":
    asyncio.run(main())
