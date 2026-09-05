#!/usr/bin/env python3
"""
task_watcher_cli.py — CLI для управления task_watcher plugin.

Команды:
  status      — статус плагина и метрики
  metrics     — метрики задач (duration, success_rate)
  top         — топ задач по длительности
  pulse       — pulse feed (лента событий)
  automation  — лог автоматизации
  rules       — правила автоматизации
  simulate    — имитировать task-событие (для тестирования)

Использование:
  python -m scripts_01.task_watcher_cli status
  python -m scripts_01.task_watcher_cli metrics
  python -m scripts_01.task_watcher_cli simulate --type task.created --task-id t1 --task-name "Deploy"
  python -m scripts_01.task_watcher_cli pulse --limit 10
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from plugins_04.task_watcher import TaskWatcherPlugin


def _create_plugin() -> TaskWatcherPlugin:
    """Создать экземпляр плагина (без EventStore и TG для CLI)."""
    return TaskWatcherPlugin()


def _cmd_status(args: argparse.Namespace) -> int:
    """Статус плагина."""
    plugin = _create_plugin()
    result = plugin.do_status()
    data = result.get("data_13", {})

    print("👁️  TASK WATCHER STATUS")
    print(f"   Name:    {data.get('name', 'task_watcher')}")
    print(f"   Enabled: {data.get('enabled', False)}")
    print(f"   Timeline events: {data.get('timeline_events', 0)}")

    metrics = data.get("metrics", {})
    print(f"\n📊 METRICS")
    print(f"   Total tasks:      {metrics.get('total_tasks', 0)}")
    print(f"   Completed:        {metrics.get('completed', 0)}")
    print(f"   Failed:           {metrics.get('failed', 0)}")
    print(f"   Success rate:     {metrics.get('success_rate', 0):.1%}")
    print(f"   Avg duration:     {metrics.get('avg_duration_seconds', 0)}s")

    counts = metrics.get("counts_by_type", {})
    if counts:
        print(f"   Counts by type:")
        for etype, count in sorted(counts.items()):
            print(f"     {etype}: {count}")

    notifications = data.get("notifications", {})
    print(f"\n🔔 NOTIFICATIONS")
    print(f"   Total sent:       {notifications.get('total_notifications', 0)}")
    print(f"   Pulse entries:    {notifications.get('pulse_entries', 0)}")
    print(f"   TG enabled:       {notifications.get('tg_enabled', False)}")

    automation = data.get("automation", {})
    print(f"\n⚡ AUTOMATION")
    print(f"   Active rules:     {automation.get('active_rules', 0)}")
    print(f"   Actions executed: {automation.get('total_actions_executed', 0)}")

    return 0


def _cmd_metrics(args: argparse.Namespace) -> int:
    """Метрики задач."""
    plugin = _create_plugin()
    result = plugin.do_metrics()
    data = result.get("data_13", {})

    print("📊 TASK METRICS")
    print(f"   Total tasks:      {data.get('total_tasks', 0)}")
    print(f"   Completed:        {data.get('completed', 0)}")
    print(f"   Failed:           {data.get('failed', 0)}")
    print(f"   Success rate:     {data.get('success_rate', 0):.1%}")
    print(f"   Avg duration:     {data.get('avg_duration_seconds', 0)}s")

    counts = data.get("counts_by_type", {})
    if counts:
        print(f"\n   Counts by type:")
        for etype, count in sorted(counts.items()):
            print(f"     {etype}: {count}")

    return 0


def _cmd_top(args: argparse.Namespace) -> int:
    """Топ задач по длительности."""
    plugin = _create_plugin()
    result = plugin.do_top_tasks(limit=args.limit)
    tasks = result.get("data_13", [])

    if not tasks:
        print("📭 No tasks with duration data")
        return 0

    print(f"🏆 TOP {len(tasks)} TASKS BY DURATION")
    print(f"   {'Task ID':15} {'Name':25} {'Duration':>10} {'Status':10}")
    print(f"   {'─' * 15} {'─' * 25} {'─' * 10} {'─' * 10}")
    for t in tasks:
        task_id = t.get("task_id", "?")[:15]
        name = t.get("task_name", "?")[:25]
        duration = t.get("duration", 0)
        status = t.get("status", "?")
        print(f"   {task_id:15} {name:25} {duration:>8.1f}s {status:10}")

    return 0


def _cmd_pulse(args: argparse.Namespace) -> int:
    """Pulse feed."""
    plugin = _create_plugin()
    result = plugin.do_pulse(limit=args.limit)
    entries = result.get("data_13", [])

    if not entries:
        print("📭 Pulse feed is empty")
        return 0

    print(f"💓 PULSE FEED ({len(entries)} entries)")
    for e in entries:
        icon = e.get("icon", "📌")
        title = e.get("title", "")
        desc = e.get("description", "")
        severity = e.get("severity", "info")
        ts = e.get("timestamp", "")[:19]

        line = f"  {icon} [{severity:7}] {title}"
        if desc:
            line += f"\n     {desc}"
        print(f"{ts} {line}")

    return 0


def _cmd_automation(args: argparse.Namespace) -> int:
    """Лог автоматизации."""
    plugin = _create_plugin()
    result = plugin.do_automation_log(limit=args.limit)
    actions = result.get("data_13", [])

    if not actions:
        print("📭 No automation actions executed yet")
        return 0

    print(f"⚡ AUTOMATION LOG ({len(actions)} actions)")
    for a in actions:
        ts = a.get("timestamp", "")[:19]
        action = a.get("action", "?")
        event_type = a.get("event_type", "?")
        task_id = a.get("task_id", "?")[:12]
        success = "✅" if a.get("success") else "❌"

        print(f"  {ts} | {success} {action:20} | {event_type:20} | task={task_id}")

    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    """Правила автоматизации."""
    plugin = _create_plugin()
    result = plugin.do_rules()
    rules = result.get("data_13", [])

    print(f"📋 AUTOMATION RULES ({len(rules)} rules)")
    for r in rules:
        status = "🟢" if r.get("enabled") else "🔴"
        print(f"  {status} {r['event_type']:25} → {r['action']}")

    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    """Имитировать task-событие."""
    plugin = _create_plugin()

    event_type = args.type
    if not event_type.startswith("task."):
        event_type = f"task.{event_type}"

    data = {
        "task_id": args.task_id,
        "task_name": args.task_name,
    }
    if args.error:
        data["error"] = args.error
    if args.duration:
        data["duration_seconds"] = args.duration

    # Создаём поддельное событие
    class FakeEvent:
        pass

    event = FakeEvent()
    event.type = event_type
    event.data = data
    event.id = f"sim-{args.task_id}"
    event.timestamp = ""
    event.metadata = {}

    plugin.on_event(event)

    print(f"✅ Simulated: {event_type}")
    print(f"   Task: {args.task_name} ({args.task_id})")
    if args.error:
        print(f"   Error: {args.error}")
    if args.duration:
        print(f"   Duration: {args.duration}s")

    # Показать что изменилось
    summary = plugin._metrics.get_summary()
    print(f"\n📊 Metrics after simulation:")
    print(f"   Total: {summary['total_tasks']}, Completed: {summary['completed']}, Failed: {summary['failed']}")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="task_watcher",
        description="Task Watcher — мониторинг task-событий (timeline, metrics, notifications, automation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Примеры:
  %(prog)s status                          Статус плагина
  %(prog)s metrics                         Метрики задач
  %(prog)s top --limit 5                   Топ-5 самых долгих задач
  %(prog)s pulse --limit 10                Последние 10 событий
  %(prog)s automation                      Лог автоматизации
  %(prog)s rules                           Правила автоматизации
  %(prog)s simulate --type task.created --task-id t1 --task-name "Deploy"
""",
    )
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Статус плагина и метрики")

    # metrics
    sub.add_parser("metrics", help="Метрики задач")

    # top
    p_top = sub.add_parser("top", help="Топ задач по длительности")
    p_top.add_argument("--limit", type=int, default=10, help="Количество (default: 10)")

    # pulse
    p_pulse = sub.add_parser("pulse", help="Pulse feed (лента событий)")
    p_pulse.add_argument("--limit", type=int, default=20, help="Количество (default: 20)")

    # automation
    p_auto = sub.add_parser("automation", help="Лог автоматизации")
    p_auto.add_argument("--limit", type=int, default=20, help="Количество (default: 20)")

    # rules
    sub.add_parser("rules", help="Правила автоматизации")

    # simulate
    p_sim = sub.add_parser("simulate", help="Имитировать task-событие")
    p_sim.add_argument(
        "--type",
        required=True,
        help="Тип события: created, started, completed, failed",
    )
    p_sim.add_argument("--task-id", required=True, help="ID задачи")
    p_sim.add_argument("--task-name", required=True, help="Имя задачи")
    p_sim.add_argument("--error", default="", help="Текст ошибки (для failed)")
    p_sim.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Длительность в секундах",
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "status": _cmd_status,
        "metrics": _cmd_metrics,
        "top": _cmd_top,
        "pulse": _cmd_pulse,
        "automation": _cmd_automation,
        "rules": _cmd_rules,
        "simulate": _cmd_simulate,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
