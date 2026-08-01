#!/bin/bash

PROJECT_DIR="/storage/emulated/0/PROJECTS/workstation/freebuff"
REPORT_FILE="$PROJECT_DIR/status_report_$(date +%Y%m%d_%H%M%S).txt"

cd "$PROJECT_DIR" || exit 1

echo "=========================================" > "$REPORT_FILE"
echo "WORKSPACE OS - STATUS REPORT" >> "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "=========================================" >> "$REPORT_FILE"

# 1. Git log последних 15 коммитов (с переименованиями)
echo -e "\n### 1. RECENT COMMITS (last 15) ###" >> "$REPORT_FILE"
git log --oneline --follow -15 >> "$REPORT_FILE" 2>&1

# 2. Git status (текущие изменения)
echo -e "\n### 2. GIT STATUS (current changes) ###" >> "$REPORT_FILE"
git status --short >> "$REPORT_FILE" 2>&1

# 3. Структура верхнего уровня
echo -e "\n### 3. TOP-LEVEL DIRECTORY STRUCTURE ###" >> "$REPORT_FILE"
ls -la >> "$REPORT_FILE" 2>&1

# 4. Python-пакеты (где есть __init__.py)
echo -e "\n### 4. PYTHON PACKAGES (with __init__.py) ###" >> "$REPORT_FILE"
find . -name "__init__.py" -not -path "*/.git/*" -not -path "*/node_modules/*" | while read f; do
    dir=$(dirname "$f")
    echo "  $dir/" >> "$REPORT_FILE"
done

# 5. Ключевые директории
echo -e "\n### 5. KEY DIRECTORIES ###" >> "$REPORT_FILE"
for dir in scripts* core* freebuff* runtime* docs* tests* api* frontend* plugins*; do
    if [ -d "$dir" ***REMOVED***; then
        echo -e "\n  --- $dir/ ---" >> "$REPORT_FILE"
        ls "$dir" >> "$REPORT_FILE" 2>&1
    fi
done

# 6. Документация (первые 10 строк ключевых файлов)
echo -e "\n### 6. KEY DOCUMENTS (first 10 lines) ###" >> "$REPORT_FILE"
for doc in docs/vision/VISION_3.0.md docs/ARCHITECTURE_MANIFEST.md docs/GLOSSARY.md docs/vision/UI_CONCEPTS.md docs/vision/IMPLEMENTATION_STATUS.md; do
    if [ -f "$doc" ***REMOVED***; then
        echo -e "\n  === $doc ===" >> "$REPORT_FILE"
        head -10 "$doc" >> "$REPORT_FILE" 2>&1
    else
        echo -e "\n  === $doc === NOT FOUND" >> "$REPORT_FILE"
    fi
done

# 7. База данных (если SQLite)
echo -e "\n### 7. DATABASE SCHEMA ###" >> "$REPORT_FILE"
if [ -f "data/context.db" ***REMOVED***; then
    sqlite3 data/context.db ".tables" >> "$REPORT_FILE" 2>&1
    sqlite3 data/context.db ".schema" >> "$REPORT_FILE" 2>&1
else
    echo "  No SQLite database found" >> "$REPORT_FILE"
fi

# 8. Плагины и рантаймы
echo -e "\n### 8. PLUGINS & RUNTIMES ###" >> "$REPORT_FILE"
if [ -d "runtime/providers" ***REMOVED***; then
    echo "  Providers:" >> "$REPORT_FILE"
    ls runtime/providers/ >> "$REPORT_FILE" 2>&1
fi
if [ -d "freebuff_plugin" ***REMOVED***; then
    echo "  Plugins:" >> "$REPORT_FILE"
    ls freebuff_plugin/ >> "$REPORT_FILE" 2>&1
fi

# 9. Зависимости
echo -e "\n### 9. DEPENDENCIES ###" >> "$REPORT_FILE"
if [ -f "requirements.txt" ***REMOVED***; then
    cat requirements.txt >> "$REPORT_FILE" 2>&1
elif [ -f "pyproject.toml" ***REMOVED***; then
    head -30 pyproject.toml >> "$REPORT_FILE" 2>&1
fi

# 10. Размер проекта
echo -e "\n### 10. PROJECT SIZE ###" >> "$REPORT_FILE"
echo "  Total files: $(find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*' | wc -l)" >> "$REPORT_FILE"
echo "  Python files: $(find . -name '*.py' -not -path '*/.git/*' | wc -l)" >> "$REPORT_FILE"
echo "  Total size: $(du -sh . | cut -f1)" >> "$REPORT_FILE"

echo -e "\n=========================================" >> "$REPORT_FILE"
echo "END OF REPORT" >> "$REPORT_FILE"
echo "=========================================" >> "$REPORT_FILE"

echo "Report generated: $REPORT_FILE"
