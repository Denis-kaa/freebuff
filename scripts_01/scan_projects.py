#!/usr/bin/env python3
"""scan_projects.py — сканирует директорию проектов и регистрирует их в системе.

Использование:
    python scripts_01/scan_projects.py                          # леviathan/opt
    python scripts_01/scan_projects.py --path /custom/path      # другой путь
    python scripts_01/scan_projects.py --rebuild                # перестроить всё с нуля
    python scripts_01/scan_projects.py --status                 # показать зарегистрированные

Что делает:
  1. Сканирует указанную директорию (по умолчанию ~/leviathan/opt)
  2. Для каждой поддиректории определяет: git-remote, README, язык, метаданные
  3. Создаёт таблицу projects в data_13/context.db
  4. Индексирует каждый проект в Knowledge Engine (FTS5 + TF-IDF)
  5. Сохраняет каждый проект в Memory Engine (MemoryLevel.PROJECT)
  6. Печатает сводку
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Пути ───────────────────────────────────────────────────────

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

DEFAULT_SCAN_PATH = Path(os.environ.get("FREEBUFF_SCAN_PATH", str(Path.home() / "leviathan" / "opt")))
DB_PATH = WORKSPACE / "data_13" / "context.db"


def detect_git_remote(project_dir: Path) -> str:
    """Read git remote origin URL."""
    git_dir = project_dir / ".git"
    if not git_dir.exists():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), "config", "--get", "remote.origin.url"],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def detect_language(project_dir: Path) -> str:
    """Detect primary language by project files."""
    has = {}
    for f in project_dir.iterdir():
        name = f.name.lower()
        if name == "requirements.txt" or name == "pyproject.toml":
            has["python"] = True
        elif name == "package.json":
            has["javascript"] = True
        elif name == "go.mod":
            has["go"] = True
        elif name == "cargo.toml":
            has["rust"] = True
        elif name == "composer.json":
            has["php"] = True
        elif name == "gemfile":
            has["ruby"] = True
        elif name == "build.gradle" or name == "pom.xml":
            has["java"] = True
        elif name.endswith(".py"):
            has["python"] = True
        elif name.endswith(".js") or name.endswith(".ts"):
            has["javascript"] = True
        elif name.endswith(".go"):
            has["go"] = True
        elif name.endswith(".rs"):
            has["rust"] = True
    # Prioritise explicit config files over extension-based detection
    for lang in ["python", "javascript", "go", "rust", "php", "ruby", "java"]:
        if has.get(lang):
            return lang
    # Fallback: count only code-file extensions, exclude non-code
    CODE_EXTS = {"py", "js", "ts", "jsx", "tsx", "go", "rs", "java", "rb", "php",
                 "c", "cpp", "h", "hpp", "swift", "kt", "scala", "sh", "bash"}
    ext_counts: dict[str, int] = {}
    try:
        for f in project_dir.iterdir():
            if f.is_file() and "." in f.name:
                ext = f.name.rsplit(".", 1)[-1].lower()
                if ext in CODE_EXTS:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
        if ext_counts:
            return max(ext_counts, key=lambda k: ext_counts[k])
    except Exception:
        pass
    return "unknown"


def read_readme(project_dir: Path) -> str:
    """Return first 300 chars of README.md if present."""
    for name in ("README.md", "README.rst", "README", "readme.md", "README.txt"):
        path = project_dir / name
        if path.exists():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                return text[:300].strip()
            except Exception:
                return ""
    return ""


def scan_projects(scan_path: Path) -> list[dict[str, Any]]:
    """Scan all directories in scan_path and extract metadata."""
    if not scan_path.is_dir():
        print(f"❌ Директория не найдена: {scan_path}", file=sys.stderr)
        return []

    projects: list[dict[str, Any]] = []

    for entry in sorted(scan_path.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("."):
            continue

        git_remote = detect_git_remote(entry)
        language = detect_language(entry)
        readme = read_readme(entry)
        has_req = (entry / "requirements.txt").exists()
        has_pkg = (entry / "package.json").exists()
        has_docker = (entry / "Dockerfile").exists()
        has_make = (entry / "Makefile").exists()
        has_pyproject = (entry / "pyproject.toml").exists()

        # Determine category
        name_lower = name.lower()
        if "leviathan" in name_lower and name_lower != "leviathan":
            category = "leviathan"
        elif any(x in name_lower for x in ["bot", "dispatcher", "messenger", "monitor"]):
            category = "telegram"
        elif any(x in name_lower for x in ["agent", "ai-", "oracle", "hub"]):
            category = "ai"
        elif any(x in name_lower for x in ["site", "web", "platform", "api"]):
            category = "web"
        elif any(x in name_lower for x in ["cockpit", "sniper", "hq"]):
            category = "tool"
        elif any(x in name_lower for x in ["secret", "backup", "server"]):
            category = "infra"
        elif any(x in name_lower for x in ["poet", "mila", "стих", "людмил"]):
            category = "personal"
        else:
            category = "other"

        projects.append({
            "name": name,
            "path": str(entry),
            "git_remote": git_remote,
            "language": language,
            "readme_preview": readme[:300],
            "has_requirements": int(has_req),
            "has_package_json": int(has_pkg),
            "has_dockerfile": int(has_docker),
            "has_makefile": int(has_make),
            "has_pyproject": int(has_pyproject),
            "category": category,
            "status": "active",
        })

    return projects


def init_db() -> sqlite3.Connection:
    """Ensure the projects table exists and return a connection."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            name TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            description TEXT DEFAULT '',
            language TEXT DEFAULT '',
            git_remote TEXT DEFAULT '',
            readme_preview TEXT DEFAULT '',
            has_requirements INTEGER DEFAULT 0,
            has_package_json INTEGER DEFAULT 0,
            has_dockerfile INTEGER DEFAULT 0,
            has_makefile INTEGER DEFAULT 0,
            has_pyproject INTEGER DEFAULT 0,
            category TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            last_scanned TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def save_projects_to_db(conn: sqlite3.Connection, projects: list[dict[str, Any]]) -> int:
    """Upsert all projects into the database. Returns count."""
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    for p in projects:
        conn.execute("""
            INSERT INTO projects (name, path, description, language, git_remote,
                                  readme_preview, has_requirements, has_package_json,
                                  has_dockerfile, has_makefile, has_pyproject,
                                  category, status, last_scanned)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                path=excluded.path,
                language=excluded.language,
                git_remote=excluded.git_remote,
                readme_preview=excluded.readme_preview,
                has_requirements=excluded.has_requirements,
                has_package_json=excluded.has_package_json,
                has_dockerfile=excluded.has_dockerfile,
                has_makefile=excluded.has_makefile,
                has_pyproject=excluded.has_pyproject,
                category=excluded.category,
                status=excluded.status,
                last_scanned=excluded.last_scanned
        """, (
            p["name"], p["path"], p["readme_preview"][:200], p["language"],
            p["git_remote"], p["readme_preview"],
            p["has_requirements"], p["has_package_json"],
            p["has_dockerfile"], p["has_makefile"], p["has_pyproject"],
            p["category"], p["status"], now,
        ))
        saved += 1
    conn.commit()
    return saved


def seed_knowledge_engine(projects: list[dict[str, Any]]) -> int:
    """Index each project into Knowledge Engine. Returns count."""
    try:
        from scripts_01.knowledge_engine import KnowledgeEngine
    except ImportError:
        print("⚠️ KnowledgeEngine недоступен — пропускаю индексацию.")
        return 0

    ke = KnowledgeEngine()
    count = 0
    for i, p in enumerate(projects):
        if (i + 1) % 10 == 0:
            print(f"   ... {i + 1}/{len(projects)}")

        content_parts = [
            f"Project: {p['name']}",
            f"Category: {p['category']}",
            f"Language: {p['language']}",
            f"Git: {p['git_remote']}",
            f"Path: {p['path']}",
        ]
        if p["readme_preview"]:
            content_parts.append(f"README: {p['readme_preview'][:300]}")

        ke.index_document(
            doc_id=f"project:{p['name']}",
            content="\n".join(content_parts),
            metadata={
                "title": p["name"],
                "source": f"projects_17/{p['category']}/{p['name']}",
                "doc_type": "project",
                "language": p["language"],
                "git_remote": p["git_remote"],
                "category": p["category"],
            },
        )
        count += 1

    # Retrain semantic index so project docs are searchable via LSA too
    try:
        ke.fit_semantic()
    except Exception as exc:
        print(f"   ⚠️ fit_semantic: {exc}")

    return count


def seed_memory_engine(projects: list[dict[str, Any]]) -> int:
    """Store each project in Memory Engine (MemoryLevel.PROJECT). Returns count."""
    try:
        from scripts_01.memory_engine import MemoryEngine, MemoryLevel, ContentType
    except ImportError:
        print("⚠️ MemoryEngine недоступен — пропускаю сохранение в память.")
        return 0

    try:
        engine = MemoryEngine()
    except PermissionError as e:
        print(f"   ⚠️ MemoryEngine: нет доступа к файловой системе ({e})")
        return 0

    count = 0
    for i, p in enumerate(projects):
        if (i + 1) % 10 == 0:
            print(f"   ... {i + 1}/{len(projects)}")

        content = json.dumps(p, ensure_ascii=False, indent=2)
        try:
            engine.store(
                level=MemoryLevel.PROJECT,
                key=f"project:{p['name']}",
                content=content,
                content_type=ContentType.JSON,
                summary=f"Project: {p['name']} ({p['category']}, {p['language']})",
                metadata={
                    "category": p["category"],
                    "language": p["language"],
                    "git_remote": p["git_remote"],
                    "path": p["path"],
                },
            )
            count += 1
        except (PermissionError, OSError) as e:
            print(f"   ⚠️ {p['name']}: {e}")

    return count


def print_summary(projects: list[dict[str, Any]]) -> None:
    """Print a categorised summary of all scanned projects."""
    categories: dict[str, list[str]] = {}
    for p in projects:
        cat = p.get("category", "other")
        categories.setdefault(cat, []).append(p["name"])

    print(f"\n{'='*60}")
    print(f"📊 Сканировано проектов: {len(projects)}")
    print(f"{'='*60}")
    for cat, names in sorted(categories.items()):
        print(f"\n  {cat}: {len(names)}")
        for n in names[:5]:
            print(f"    • {n}")
        if len(names) > 5:
            print(f"    ... и ещё {len(names) - 5}")
    print(f"\n{'='*60}\n")


def show_status() -> None:
    """Show registered projects from the database."""
    conn = init_db()
    rows = conn.execute(
        "SELECT name, category, language, git_remote, status, last_scanned FROM projects ORDER BY category, name"
    ).fetchall()
    conn.close()

    if not rows:
        print("📭 В базе нет зарегистрированных проектов.")
        return

    print(f"\n{'='*60}")
    print(f"📋 Проекты в реестре: {len(rows)}")
    print(f"{'='*60}")
    for name, category, language, git_remote, status, last_scanned in rows:
        git_short = git_remote.split("/")[-1].replace(".git", "") if git_remote else "local"
        print(f"  {name:<30} {category:<10} {language:<12} {git_short:<25} {status}")
    print(f"{'='*60}\n")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Сканирует директорию проектов и регистрирует их в системе",
    )
    parser.add_argument("--path", default=str(DEFAULT_SCAN_PATH),
                        help="Путь к директории с проектами")
    parser.add_argument("--rebuild", action="store_true",
                        help="Пересканировать и переиндексировать все проекты")
    parser.add_argument("--status", action="store_true",
                        help="Показать зарегистрированные проекты")
    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.rebuild:
        print("🧹 Очистка Knowledge Engine...")
        try:
            from scripts_01.knowledge_engine import KnowledgeEngine
            ke = KnowledgeEngine()
            ke.clear()
        except Exception as exc:
            print(f"   ⚠️ {exc}")
        print("🧹 Очистка Memory Engine (project) ...")
        try:
            from scripts_01.memory_engine import MemoryEngine, MemoryLevel
            me = MemoryEngine()
            for entry in me.list_entries(level=MemoryLevel.PROJECT):
                me.delete(MemoryLevel.PROJECT, entry.key)
        except Exception as exc:
            print(f"   ⚠️ {exc}")

    scan_path = Path(args.path).expanduser().resolve()
    if not scan_path.is_dir():
        print(f"❌ Директория не найдена: {scan_path}")
        return 1

    print(f"🔍 Сканирую: {scan_path}")
    projects = scan_projects(scan_path)

    if not projects:
        print("❌ Проекты не найдены.")
        return 1

    # 1. DB
    print(f"💾 Сохраняю {len(projects)} проектов в БД ...")
    conn = init_db()
    saved = save_projects_to_db(conn, projects)
    conn.close()
    print(f"   ✅ Записано: {saved}")

    # 2. Knowledge Engine
    print("🧠 Индексирую в Knowledge Engine ...")
    indexed = seed_knowledge_engine(projects)
    print(f"   ✅ Проиндексировано: {indexed}")

    # 3. Memory Engine
    print("📝 Сохраняю в Memory Engine ...")
    stored = seed_memory_engine(projects)
    print(f"   ✅ Сохранено: {stored}")

    # 4. Summary
    print_summary(projects)

    print(f"\n{'='*60}")
    print("✅ Готово. Теперь Buffy знает о всех проектах через:")
    print("   • data_13/context.db → таблица projects")
    print("   • Knowledge Engine → поиск project:*")
    print("   • Memory Engine → MemoryLevel.PROJECT")
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
