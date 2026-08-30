#!/usr/bin/env python3
"""
MCP-сервер телефона для Buffy / AI-агентов.
Запускать в Termux: python phone_mcp_server.py

Источник: /storage/emulated/0/1.md

Инструменты (8 шт):
  - phone_battery      — заряд батареи
  - phone_storage      — занятость хранилища
  - phone_sms_list     — последние SMS
  - phone_camera_photo — фото на камеру
  - phone_run_command  — shell-команда
  - phone_read_file    — прочитать файл
  - phone_list_dir     — листинг директории
  - phone_gps_location — GPS-координаты

Транспорт: stdio (стандартный MCP)
Туннель: ssh -R 9400:localhost:9400 user@leviathanstory.ru
"""

import asyncio
import json
import os
import shlex
import subprocess
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# ── Инструменты ──────────────────────────────────────────────

# Default Android shared storage path. Override with PHONE_STORAGE_ROOT env var.
PHONE_STORAGE_ROOT = os.environ.get("PHONE_STORAGE_ROOT", "/storage/emulated/0")

TOOLS = [
    types.Tool(
        name="phone_battery",
        description="Уровень заряда батареи и статус",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="phone_storage",
        description="Занятость хранилища телефона",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="phone_sms_list",
        description="Последние SMS (кол-во задаётся параметром limit)",
        inputSchema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Сколько SMS показать", "default": 10}
            },
        },
    ),
    types.Tool(
        name="phone_camera_photo",
        description="Сделать фото на камеру и сохранить файл",
        inputSchema={
            "type": "object",
            "properties": {
                "camera_id": {"type": "integer", "description": "0 — задняя, 1 — фронтальная", "default": 0}
            },
        },
    ),
    types.Tool(
        name="phone_run_command",
        description="Выполнить любую shell-команду на телефоне",
        inputSchema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Команда для Termux"}
            },
            "required": ["command"],
        },
    ),
    types.Tool(
        name="phone_read_file",
        description="Прочитать файл на телефоне",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Абсолютный путь к файлу"}
            },
            "required": ["path"],
        },
    ),
    types.Tool(
        name="phone_list_dir",
        description="Листинг директории на телефоне",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Путь к директории", "default": "/storage/emulated/0"}
            },
        },
    ),
    types.Tool(
        name="phone_gps_location",
        description="Текущие GPS-координаты телефона (через termux-location)",
        inputSchema={"type": "object", "properties": {}},
    ),
]


def run_termux(cmd: str, timeout: int = 15) -> str:
    """Выполнить команду в Termux и вернуть stdout."""
    result = subprocess.run(
        ["sh", "-c", cmd],
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "PATH": "/data/data/com.termux/files/usr/bin:" + os.environ.get("PATH", "")},
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ошибка ({result.returncode}): {result.stderr.strip()}")
    return result.stdout


async def handle_tool_call(name: str, arguments: dict) -> list[types.TextContent]:
    """Обработчик вызова инструмента."""
    try:
        if name == "phone_battery":
            out = run_termux("termux-battery-status")
            data = json.loads(out)
            return [types.TextContent(type="text", text=json.dumps(data, indent=2, ensure_ascii=False))]

        elif name == "phone_storage":
            out = run_termux(f"df -h {shlex.quote(PHONE_STORAGE_ROOT)} \"$HOME\"")
            return [types.TextContent(type="text", text=out)]

        elif name == "phone_sms_list":
            limit = arguments.get("limit", 10)
            out = run_termux(f"termux-sms-list -l {limit}")
            return [types.TextContent(type="text", text=out)]

        elif name == "phone_camera_photo":
            cam = arguments.get("camera_id", 0)
            path = f"/storage/emulated/0/DCIM/mcp_photo_{asyncio.get_event_loop().time():.0f}.jpg"
            run_termux(f"termux-camera-photo -c {cam} {path}")
            return [types.TextContent(type="text", text=f"Фото сохранено: {path}")]

        elif name == "phone_run_command":
            cmd = arguments["command"]
            out = run_termux(cmd, timeout=30)
            return [types.TextContent(type="text", text=out[:5000])]  # обрезаем вывод

        elif name == "phone_read_file":
            path = arguments["path"]
            out = run_termux(f"cat '{path}'")
            return [types.TextContent(type="text", text=out[:10000])]

        elif name == "phone_list_dir":
            path = arguments.get("path", "/storage/emulated/0")
            out = run_termux(f"ls -la '{path}'")
            return [types.TextContent(type="text", text=out[:5000])]

        elif name == "phone_gps_location":
            out = run_termux("termux-location")
            return [types.TextContent(type="text", text=out[:2000])]

        else:
            raise ValueError(f"Неизвестный инструмент: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Ошибка: {str(e)}")]


async def main():
    server = Server("phone-mcp-server")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        return await handle_tool_call(name, arguments)

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="phone-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
