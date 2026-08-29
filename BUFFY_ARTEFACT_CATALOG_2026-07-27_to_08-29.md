# BUFFY ARTEFACT CATALOG (2026-07-27 → 2026-08-29)

> 来源：buffy_history_full.md（58场对话）+ 仓库文件系统时间戳 + CHANGELOG.md 版本记录
> 说明：按类别整理所有可确认的产物，每条附创建/修改日期

---

## 一、系统级 Meta-промты（pompts_11/）

| 日期 | 文件 | 内容 |
|------|------|------|
| 07-27 | 002_14_planirovshchik_arhitekt.md | 规划师架构师 |
| 07-27 | 001_07_pravila_dokumentirovaniya.md | 文档规范 |
| 07-29 | 003~016（一批） | 平台核心设计系列（DPE、架构重组、工程记忆等） |
| 07-31 | 022~031（一批） | Workspace OS 核心域模型系列（reality check、域模型、知识管理、审计） |
| 08-01 | 033~043（一批） | DPE 审计/实现、consolidation pipeline、code quality standard、UI |
| 08-02 | 044~047 | canonical history、MCP phone control、tripwire、e2e 测试 |
| 08-04 | 048~050、059 | 平台重写指令、TG 自主调用 + handoff、TG 外部接口 |
| 08-05 | 051~058 | 组织记忆引擎、RFC 演进、ARB/AG 治理、forge 元系统、优先级三债 |
| 08-06 | 060~061 | telegram bot aiogram、forge leviathan roadmap |
| 08-08 | 063~066 | vkusvill demo/研究/自动化、workspace os kus |
| 08-09 | 067 | design taxonomy v0.1 |
| 08-10 | 068~071 | autonomous project executor、first vertical slice、lead aggregator、prompt architect 1.7 |
| 08-11 | 072~078 | content intelligence、factory/forge 文档化、lisa estimator、factory registry 等 |
| 08-12 | 079~082 | opportunity engine、whim capture、model dispatcher、doc code sync |
| 08-13 | 083 | promt83 protocols |
| 08-16 | 084~085 | intelligence integration forensics、close intelligence loop |
| 08-17 | 086~094 | opportunity ranking、phase6~10 系列（contract forensics、vertical slice 等） |
| 08-20 | 096~103 | corpus persistence、capability gap auditor、hypothesis ledger、pricing enumerator、weighted scoring、devil advocate、forensic reporter |
| 08-21 | 104~106 | platform forensics v2、repo org forensics、repo forensics system modeling |
| 08-22 | 107~108 | platform inventory、artifact contract |
| 08-23 | 110 | sandbox tool acl ADR021 |
| 08-24 | 109 | （独立文件） |
| 08-27 | 113 | ai-dubber 相关 |
| 08-29 | 116 | meta-промт：human 回复写作 v1（29 节，27KB） |
| 08-29 | 117 | meta-промт v2.0：11 块架构，few-shot 对比示例，~2x 精简 |

## 二、平台核心代码（core_02/ + scripts_01/）

| 日期 | 文件 | 内容 |
|------|------|------|
| 08-20 | scripts_01/pricing_enumerator.py | 定价枚举器 |
| 08-20 | scripts_01/weighted_scoring_engine.py | 加权评分引擎 |
| 08-20 | scripts_01/research_factory.py | 研究 factory |
| 08-20 | scripts_01/devil_advocate_pass.py | 魔鬼代言人 pass |
| 08-20 | scripts_01/hypothesis_ledger.py | 假设账本 |
| 08-22 | core_02/forge_registry.py | forge 注册表 |
| 08-22 | core_02/factory_base.py | factory 基类 |
| 08-22 | core_02/artifact.py | artifact 契约 |
| 08-22 | core_02/agent_base.py | agent 基类 |
| 08-22 | core_02/integration_base.py | integration 基类 |
| 08-22 | core_02/workspace_registry.py | workspace 注册表 |
| 08-23 | core_02/tool_acl.py + scripts_01/tool_runtime.py | 工具 ACL + 运行时 |
| 08-25 | core_02/remote_db.py | 远程 DB |
| 08-25 | core_02/memory_store.py | 记忆存储 |
| 08-25 | scripts_01/context_manager.py | 上下文管理器（重写版） |
| 08-29 | scripts_01/tui_history_import.py | TUI 历史导入 context.db/events.db |

## 三、工程记忆文档（docs_10/engineering-memory/）

| 日期 | 文件 | 内容 |
|------|------|------|
| 08-22 | ARCHITECTURAL_BASELINE_V1.md | 架构基线 v1 |
| 08-22 | ARCHITECTURE_DECISION_108_V1.md | 决策 108 |
| 08-22 | ARTIFACT_CONTRACT_DESIGN_V1.md | artifact 契约设计 |
| 08-22 | BASELINE_V1_CODE_VERIFICATION.md | 基线代码验证 |
| 08-22 | COMPETING_ABSTRACTIONS_MATRIX_V1.md | 竞争抽象矩阵 |
| 08-22 | CONTRACT_GRAPH_V1.md | 契约图 |
| 08-22 | FACTORY_FORGE_ARCHITECTURE_V1.md | factory/forge 架构 |
| 08-22~23 | AUDIT_WS_OS_P65_§4~§14_V1.md（11 个） | P65 §4~§14 审计系列 |

## 四、平台项目（projects_17/）

| 日期 | 项目 | 产物 |
|------|------|------|
| 08-17 | kwork_site | MANIFEST、бриф 解析、项目骨架 |
| 08-18 | sheet_project | 任务.md、CON-60、Blueprint v3 chain |
| 08-20 | vocal | 能力实体 + 14 missing_registry 注册 |
| 08-23 | imperial_phuket | clone audit/estimate、handoff README/letter、media verification、CLONE_STATUS |
| 08-23 | public_request_parser | spec（191 消息最大会话） |
| 08-24 | python_mentor | MANIFEST、SPEC、project.yaml、PHASE_BC_PLAN、FSRS_NOTE、完整项目骨架 |
| 08-24 | severny_chay | main.py + test_api_chat.py + test_e2e_http.py（AI 助手后端） |
| 08-24 | whimco | WHIMCO_SERVER_REPORT.md |
| 08-25 | diet_platform | PROJECT_DUMP.md |
| 08-28 | profile_site | README、design_manifest.yaml、DEPLOY.md |
| 08-28 | anti-slop | CHANGELOG、README（npm 包 + CI） |

## 五、Kwork / 求职 / 反顺 slop 产物（根目录）

| 日期 | 文件 | 内容 |
|------|------|------|
| 08-28 | phone-file-inventory.txt | 手机文件清单 |
| 08-28 | career-profile-spec.md | 职业档案 spec |
| 08-28 | resume-mitlis.md / resume-draft.md / resume-one-page.md | 简历草稿系列 |
| 08-28 | resume-one-page-hh.md/.html/.pdf | HH 一页简历（三格式） |
| 08-28 | cover-letter-template.md + cover-letters-dipra-ads-luis.md | cover letter 模板 + 实例 |
| 08-28 | rare-vacancies-portfolio-plan.md | 稀缺岗位作品集计划 |
| 08-28 | hh-headlines-summaries.md | HH 职位标题摘要 |
| 08-28 | client-projects-permissions.md | 客户项目权限说明 |
| 08-28 | anti-slop-design-system.md（+.bak） | 反 slop 设计系统 |
| 08-28 | leviathan-projects-readiness-report.md | leviathan 项目就绪报告 |
| 08-28 | profile-card-site-spec.md / profile-site-design-prompts.md / profile-site-redesign-spec.md | profile site 设计系列 |
| 08-29 | interview_ai_prompt_engineer.md | AI prompt 工程师面试 |
| 08-29 | neiroslop_research.md | 神经 slop 研究 |
| 08-29 | otklik_kwork_ai_assistent.md | Kwork AI 助手 отклик |
| 08-29 | ai_dubber_transcript_sport_records.txt | ai-dubber Whisper 转录 |
| 08-29 | FORENSICS_FULL_2026-08-29.md | 平台全量 форенсик |
| 08-29 | FORENSICS_BUFFY_HISTORY_2026-08-29.md | Buffy 历史 форенсик |
| 08-29 | buffy_history_full.md + buffy_history_index.jsonl | 统一历史 дамп + 索引 |
| 08-29 | BUFFY_TIMELINE_2026-07-27_to_08-29.md | 任务 хронология |
| 08-29 | BUFFY_SESSION_SUMMARY_2026-07-27_to_08-29.md | 逐会话 резюме |

## 六、版本发布（CHANGELOG.md）

| 日期 | 版本 | 备注 |
|------|------|------|
| 07-28 | 2.6.0 → 4.10.0 | 初始版本爆发（约 40 个版本） |
| 07-29 | 4.x → 5.9.0 | 5.x 系列启动 |
| 07-30 | 5.10.0 → 5.24.x | 快速迭代 |
| 07-31 | 5.25.0 → 5.25.1 | |
| 08-01 | 5.26.0 → 5.36.0 | 11 个版本 |
| 08-02 | 5.37.0 → 5.43.0 | 含 v5.37.1（bug fix） |
| 08-03 | 5.46.0 → 5.59.0 | TASK.md 对齐此版本 |
| 08-20 | 5.189.53 → 5.189.67 | forge/factory 密集发布（15 个） |
| 08-21 | 5.189.68 → 5.189.69 | |
| 08-22 | 5.189.70 → 5.189.77 | 8 个版本 |
| 08-24 | 5.189.84 | 最新 |

## 七、归档 / 取证快照（根目录 tar.gz 系列）

| 日期 | 文件 | 内容 |
|------|------|------|
| 08-08~09 | vkusvill_vacancy_work_*.tar.gz | vkusvill 工作快照 |
| 08-10 | promts_59_67_complete_work_*.tar.gz | промт 59-67 快照 |
| 08-11 | factory_forge_architecture_work_*.tar.gz | factory/forge 架构快照 |
| 08-13 | promt4_archive_v1.tar.gz | промт 4 归档 |
| 08-14 | PHASE4_EVALUATION_2026-08-14.tar.gz | Phase 4 评估 |
| 08-16 | PHASE4_EVALUATION_2026-08-16.tar.gz + INTELLIGENCE_INTEGRATION_FORENSICS_V1.tar.gz | |
| 08-17 | PHASE5~PHASE8 系列（4 个 tar.gz） | intelligence loop、code contract forensics、evaluation |
| 08-18 | PHASE9/12/13 系列（4 个 tar.gz + manifest） | factory 实现、basefactory 重构、G116 |
| 08-21~22 | FORENSICS_104_105_106_107 系列（4 个 tar.gz） | 架构 forensics 快照 |
| 08-22 | platform_architectural_inventory_34.tar.gz | 平台清单快照 |
| 08-21 | PLATFORM_ARCHITECTURE_FORENSICS_v5.189.69_promt106.zip | |

## 八、平台记忆（本次导入新增）

| 日期 | 位置 | 内容 |
|------|------|------|
| 08-29 | data_13/context.db | +58 TUI 会话（53 phone + 5 server），3894 条消息 |
| 08-29 | context_12/events.db | +58 条 tui.session.imported 事件 |

> 注：此导入使平台记忆（context.db/events.db）首次看到 TUI-客户端的完整工作历史，
> 填补了 events.db 自 08-23 以来的静默缺口。

---

## 统计摘要

- **промты**：pompts_11/ 111 个 .md（001~117，缺 086/087 编号空缺、018~021 未创建）
- **版本**：从 2.6.0 到 5.189.84，约 200+ 个版本
- **核心代码**：core_02/ 10 个新模块 + scripts_01/ 15+ 个新脚本（8 月）
- **工程记忆**：7 个 V1 设计文档 + 11 个 P65 审计
- **项目**：11 个活跃项目（projects_17/）
- **根目录产物**：30+ 个（Kwork/求职/anti-slop/форенсик）
- **归档快照**：15+ 个 tar.gz
