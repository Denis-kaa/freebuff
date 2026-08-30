# Карта восстановления коррупции `***REMOVED***`

Дата: 2026-08-30. Повреждено tracked-файлов: **1232**, маркеров: **54051**.

## Важное уточнение

Ранее фигурировала цифра 534, но текущий полный подсчёт показывает 535 повреждённых `.py` и 1232 файла всех типов. Восстановление не выполнялось.

## Распределение по расширениям

- `.md`: 541
- `.py`: 535
- `.json`: 49
- `.sh`: 27
- `.tsx`: 12
- `.yaml`: 11
- `.ts`: 8
- `.html`: 7
- `.dart`: 5
- `.toml`: 5
- `.css`: 4
- `.txt`: 4
- `<none>`: 3
- `.ini`: 3
- `.kts`: 3
- `.j2`: 3
- `.js`: 2
- `.mmd`: 2
- `.xml`: 2
- `.yml`: 1
- `.backup_before_restore`: 1
- `.svg`: 1
- `.jsonl`: 1
- `.sql`: 1
- `.0_holistic`: 1

## Распределение по верхним каталогам

- `projects_17`: 452
- `docs_10`: 189
- `tests_09`: 135
- `scripts_01`: 101
- `pompts_11`: 61
- `freebuff_plugin_03`: 51
- `core_02`: 39
- `trash_21`: 38
- `buffy-playground_19`: 12
- `runtime_05`: 12
- `phase5_intelligence_loop_26`: 11
- `books_out_23`: 9
- `phase6_code_contract_forensics_27`: 9
- `plugins_04`: 8
- `phase4_evaluation_24`: 7
- `phase8_evaluation_29`: 7
- `architecture_forensics_v2`: 6
- `intelligence_forensics_25`: 6
- `phase7_evaluation_28`: 6
- `phase9_implementation_continuation_31`: 4
- `.freebuff`: 3
- `FORENSICS_104_105_106_107`: 3
- `phase9_evaluation_30`: 3
- `platform_architectural_inventory_34`: 3
- `prototype_22`: 3
- `system_model_forensics_33`: 3
- `services_08`: 2
- `src_06`: 2
- `.freebuff_result`: 1
- `.github`: 1
- `.gitignore`: 1
- `AGENTS.md`: 1
- `BUFFY.md`: 1
- `BUFFY_PROJECT.md`: 1
- `BUFFY_UNFINISHED_TAILS_2026-07-27_to_08-29.md`: 1
- `CHANGELOG.md`: 1
- `CHANGELOG.md.backup_before_restore`: 1
- `PHASE12_G116_CODE_ROUTING_MANIFEST.md`: 1
- `PLATFORM.md`: 1
- `SESSION_UNDERSTANDING_2026-08-02.md`: 1
- `SPEC.md`: 1
- `TASK.md`: 1
- `anti-slop-design-system.md`: 1
- `buffy_history_full.md`: 1
- `buffy_history_index.jsonl`: 1
- `cli_07`: 1
- `client-projects-permissions.md`: 1
- `cover-letter-template.md`: 1
- `freebuff-sync-spec.md`: 1
- `freebuff_cli.py`: 1
- `freebuff_plugin`: 1
- `frontend_18`: 1
- `generate_project_dump.sh`: 1
- `imperial_phuket_CLONE_STATUS.md`: 1
- `imperial_phuket_clone_audit_estimate.md`: 1
- `imperial_phuket_handoff_README.md`: 1
- `imperial_phuket_handoff_letter_template.md`: 1
- `infa_20`: 1
- `interview_ai_prompt_engineer.md`: 1
- `leviathan-projects-readiness-report.md`: 1
- `mypy.ini`: 1
- `phone-file-inventory.txt`: 1
- `profile-site-design-prompts.md`: 1
- `public-request-parser-spec.md`: 1
- `repository_organization_forensics_32`: 1
- `resume-one-page-hh.html`: 1
- `run_checks.py`: 1
- `run_tests_fast.sh`: 1
- `setup_canonical.sh`: 1
- `smart_test_runner.sh`: 1
- `smart_test_runner_fixed.sh`: 1
- `status_report.sh`: 1
- `steps.md`: 1
- `tank.html`: 1
- `verify_archive.sh`: 1

## Источники восстановления

- **Высокая уверенность, 19 файлов:** найден одноимённый файл в `trash_21/dump_20260801_222022/`. Нужно сравнить даты и содержимое перед восстановлением.
- **Потенциальный источник Git, 1213 файлов:** есть история файла, но автоматического чистого состояния не подтверждено. Для каждого файла требуется найти последний blob без маркера.
- **`trash_21` как источник целиком не подтверждён:** он сам содержит повреждённые файлы и не должен считаться чистым бэкапом без проверки.
- **Серверный бэкап:** ранее подтверждены только `.env` и базы данных, исходники в доступном бэкапе не обнаружены.

## Статус

Карта создана; ремонт и перезапись истории не выполнялись. Следующий безопасный шаг: автоматически проверить Git-историю каждого файла и сохранить только подтверждённые clean blobs в отдельный каталог, без изменения рабочего дерева.
