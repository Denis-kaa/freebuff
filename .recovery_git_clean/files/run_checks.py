import os
import subprocess
import sys
***REMOVED***

# 1) Append PB-17
lessons = Path('core_02/LESSONS.md')
existing = lessons.read_text(encoding='utf-8')
payload = Path('/tmp/pb17_payload.txt').read_text(encoding='utf-8').rstrip() + '\n'
if '## 📦 Scenario: flake root-cause' in existing:
    print('=== 1) SKIP: PB-17 block already present ===')
else:
    new_content = existing.rstrip('\n') + '\n\n' + payload
    lessons.write_text(new_content, encoding='utf-8')
    print(f'=== 1) WROTE: {lessons***REMOVED***, new size {lessons.stat().st_size***REMOVED*** bytes ===')

# 2) Marker verification
print('\n=== 2) PB-17 marker verification ===')
***REMOVED***
match = re.search(r'PB-17 — Forge Pipeline', lessons.read_text())
print(f"Marker found: {bool(match)***REMOVED***")

# 3) test_run_skip_stage fix verification
print('\n=== 3) test_run_skip_stage fix verification ===')
content = Path('tests_09/test_forge_pipeline.py').read_text()
idx = content.find('def test_run_skip_stage')
print(content[idx:idx+150***REMOVED***)

# 4) Targeted regression
print('\n=== 4) targeted regression — test_run_skip_stage isolated 3x ===')
for i in range(1, 4):
    res = subprocess.run(['python3', '-m', 'pytest', 'tests_09/test_forge_pipeline.py::TestPipelineRun::test_run_skip_stage', '-q', '--tb=line'***REMOVED***, capture_output=True, text=True)
    print(f"  iso #{i***REMOVED***: {res.stdout.strip() or res.stderr.strip()***REMOVED***")

# 5) Full batch regression
print('\n=== 5) full batch regression (4 test files) ===')
files = ['tests_09/test_forge_pipeline.py', 'tests_09/test_forge_registry.py', 'tests_09/test_wizard.py', 'tests_09/test_scenario_registry.py'***REMOVED***
res = subprocess.run(['python3', '-m', 'pytest'***REMOVED*** + files + ['-q', '--tb=line', '-p', 'no:randomly'***REMOVED***, capture_output=True, text=True)
print(res.stdout.splitlines()[-1***REMOVED*** if res.stdout else res.stderr)

# 6) Opt-in gate: doc_code_verify --strict (additive, §L.4 step 4 / §J.4).
#    WARN по умолчанию; --strict блокирует при STALE/DOC_ONLY.
#    Запуск: DOC_CODE_STRICT=1 python run_checks.py
if os.environ.get('DOC_CODE_STRICT') == '1':
    print('\n=== 6) doc_code_verify --strict gate (opt-in) ===')
    res = subprocess.run(
        ['python3', '-m', 'core_02.doc_code_verify', 'docs_10/engineering-memory/', '--strict'***REMOVED***,
        capture_output=True, text=True,
    )
    print(res.stdout or res.stderr)
    if res.returncode != 0:
        print('GATE FAILED: STALE/DOC_ONLY anchors found (--strict)')
        sys.exit(res.returncode)
    print('GATE OK')
