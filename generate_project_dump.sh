#!/bin/bash

PROJECT_DIR="/storage/emulated/0/PROJECTS/workstation/freebuff"
DUMP_FILE="$PROJECT_DIR/project_dump_$(date +%Y%m%d_%H%M%S).md"
ARCHIVE_DIR="$PROJECT_DIR/docs_10/audits/dump_$(date +%Y%m%d_%H%M%S)"

cd "$PROJECT_DIR" || exit 1

# Создаем папку для архива
mkdir -p "$ARCHIVE_DIR"

echo "🔍 Generating Workspace OS Project Dump..."
echo "📁 Archive: $ARCHIVE_DIR"
echo " Dump file: $DUMP_FILE"

# Заголовок дампа
cat > "$DUMP_FILE" << 'HEADER'
#  WORKSPACE OS - COMPLETE PROJECT DUMP

**Generated:** $(date)  
**Purpose:** External audit and competitive analysis  
**Project:** Buffy/Workspace OS - AI Infrastructure Layer  

---

##  TABLE OF CONTENTS

1. [Vision & Architecture***REMOVED***(#1-vision--architecture)
2. [Core Implementation***REMOVED***(#2-core-implementation)
3. [Plugin System***REMOVED***(#3-plugin-system)
4. [Runtime & Adapters***REMOVED***(#4-runtime--adapters)
5. [Documentation***REMOVED***(#5-documentation)
6. [Examples & Use Cases***REMOVED***(#6-examples--use-cases)

---

HEADER

# 1. VISION & ARCHITECTURE
echo "## 1. VISION & ARCHITECTURE" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"

for doc in docs_10/vision/VISION_3.0.md docs_10/core/ARCHITECTURE_MANIFEST.md docs_10/core/GLOSSARY.md BUFFY.md README.md; do
    if [ -f "$doc" ***REMOVED***; then
        echo "### 📄 $doc" >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        echo '```markdown' >> "$DUMP_FILE"
        head -200 "$doc" >> "$DUMP_FILE" 2>/dev/null
        echo '```' >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        cp "$doc" "$ARCHIVE_DIR/" 2>/dev/null
    fi
done

# 2. CORE IMPLEMENTATION
echo "## 2. CORE IMPLEMENTATION" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"

# Key scripts
for script in scripts_01/work_area_view.py scripts_01/memory_engine.py scripts_01/knowledge_engine.py scripts_01/graph_index.py scripts_01/model_gateway.py scripts_01/event_bus.py scripts_01/mcp_server.py scripts_01/orchestrator.py scripts_01/roles.py scripts_01/presence.py scripts_01/collaboration.py; do
    if [ -f "$script" ***REMOVED***; then
        echo "###  $script" >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        echo '```python' >> "$DUMP_FILE"
        head -150 "$script" >> "$DUMP_FILE" 2>/dev/null
        echo '```' >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        mkdir -p "$ARCHIVE_DIR/scripts_01"
        cp "$script" "$ARCHIVE_DIR/scripts_01/" 2>/dev/null
    fi
done

# Core modules
for core in core_02/router.py core_02/interfaces.py; do
    if [ -f "$core" ***REMOVED***; then
        echo "### 🐍 $core" >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        echo '```python' >> "$DUMP_FILE"
        cat "$core" >> "$DUMP_FILE" 2>/dev/null
        echo '```' >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        mkdir -p "$ARCHIVE_DIR/core_02"
        cp "$core" "$ARCHIVE_DIR/core_02/" 2>/dev/null
    fi
done

# 3. PLUGIN SYSTEM
echo "## 3. PLUGIN SYSTEM" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"

for plugin in freebuff_plugin_03/__init__.py freebuff_plugin_03/bridge.py freebuff_plugin_03/bridge_layer.py freebuff_plugin_03/scenario_engine.py freebuff_plugin_03/acp_protocol.py; do
    if [ -f "$plugin" ***REMOVED***; then
        echo "### 🐍 $plugin" >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        echo '```python' >> "$DUMP_FILE"
        head -150 "$plugin" >> "$DUMP_FILE" 2>/dev/null
        echo '```' >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        mkdir -p "$ARCHIVE_DIR/freebuff_plugin_03"
        cp "$plugin" "$ARCHIVE_DIR/freebuff_plugin_03/" 2>/dev/null
    fi
done

# 4. RUNTIME & ADAPTERS
echo "## 4. RUNTIME & ADAPTERS" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"

if [ -f "freebuff_plugin_03/runtime/adapters/adapter.py" ***REMOVED***; then
    echo "###  Runtime Adapter Base" >> "$DUMP_FILE"
    echo "" >> "$DUMP_FILE"
    echo '```python' >> "$DUMP_FILE"
    cat "freebuff_plugin_03/runtime/adapters/adapter.py" >> "$DUMP_FILE" 2>/dev/null
    echo '```' >> "$DUMP_FILE"
    echo "" >> "$DUMP_FILE"
fi

# 5. DOCUMENTATION
echo "## 5. DOCUMENTATION" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"

for doc in docs_10/core/ARCHITECTURE_PRINCIPLES.md docs_10/core/LIFECYCLE.md docs_10/decisions/ADR_001_Vision_3.0_AI_Infrastructure_Layer.md; do
    if [ -f "$doc" ***REMOVED***; then
        echo "### 📄 $doc" >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
        echo '```markdown' >> "$DUMP_FILE"
        head -100 "$doc" >> "$DUMP_FILE" 2>/dev/null
        echo '```' >> "$DUMP_FILE"
        echo "" >> "$DUMP_FILE"
    fi
done

# 6. EXAMPLES & USE CASES
echo "## 6. EXAMPLES & USE CASES" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"

if [ -f "TASK.md" ***REMOVED***; then
    echo "### 📋 Current TASK.md" >> "$DUMP_FILE"
    echo "" >> "$DUMP_FILE"
    echo '```markdown' >> "$DUMP_FILE"
    cat "TASK.md" >> "$DUMP_FILE" 2>/dev/null
    echo '```' >> "$DUMP_FILE"
    echo "" >> "$DUMP_FILE"
fi

if [ -f "CHANGELOG.md" ***REMOVED***; then
    echo "###  Recent CHANGELOG (last 200 lines)" >> "$DUMP_FILE"
    echo "" >> "$DUMP_FILE"
    echo '```markdown' >> "$DUMP_FILE"
    tail -200 "CHANGELOG.md" >> "$DUMP_FILE" 2>/dev/null
    echo '```' >> "$DUMP_FILE"
    echo "" >> "$DUMP_FILE"
fi

# Summary
echo "" >> "$DUMP_FILE"
echo "---" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"
echo "## 📊 PROJECT STATISTICS" >> "$DUMP_FILE"
echo "" >> "$DUMP_FILE"
echo "- **Total files:** $(find . -type f -not -path '*/.git/*' -not -path '*/node_modules/*' | wc -l)" >> "$DUMP_FILE"
echo "- **Python files:** $(find . -name '*.py' -not -path '*/.git/*' | wc -l)" >> "$DUMP_FILE"
echo "- **Total size:** $(du -sh . | cut -f1)" >> "$DUMP_FILE"
echo "- **Documentation files:** $(find docs_10 -name '*.md' | wc -l)" >> "$DUMP_FILE"
echo "- **Test files:** $(find tests_09 -name '*.py' | wc -l)" >> "$DUMP_FILE"

echo ""
echo "✅ Dump generated successfully!"
echo "📄 File: $DUMP_FILE"
echo "📁 Archive: $ARCHIVE_DIR"
echo ""
echo "To create compressed archive:"
echo "  tar -czf project_dump.tar.gz -C $ARCHIVE_DIR ."
