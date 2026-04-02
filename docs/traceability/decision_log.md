# Decision Log

本文件记录已经冻结、并且会约束后续实现的工程决策。

## 2026-03-31 Initialization

- 公共时间模块归属 `src/unit/time`，命名空间固定为 `unit::time`。
- 第一阶段只对 `unit::time` 做代码与测试闭环，Navigation / Prediction / Mission Planning 先冻结边界。
- 方法型 skills 直接拷贝进本仓库，避免外部引用漂移。
- `pppar-expert` 以 `/home/hotdry/projects/PRIDE-PPPAR` 为唯一权威知识源。
- Meson 三方依赖管理按参考项目预铺完整骨架，但当前实现尽量仅依赖标准库。

## 2026-04-01 Traceability Split

- `docs/traceability/` 只保留人工治理文档。
- `docs/_generated/traceability/` 只保留工具生成的证据与覆盖率报表。
- 默认工作流改为 skills 常驻、MCP CLI 手动运行，不再依赖 Codex 启动时自动注册项目 MCP。

## 2026-04-01 Collaboration Entry And Gates

- 仓库级协作入口固定为根目录 `AGENTS.md`。
- 不新增 `.codex/rules/`；项目规则统一由 `AGENTS.md` 与 `docs/architecture/agent-collaboration.md` 承载。
- 本地质量门禁统一收敛到 `python3 scripts/check_quality.py --report-json`。
- 验收前必须经过 build、test、traceability 与标签完整性检查。

## 2026-04-02 Git, CI, And Benchmark Baseline

- 仓库已初始化为 git repository，默认分支策略固定为 `main` / `develop` / `feature/<task-id>-<topic>`。
- 仓库级 CI 只调用 repo-local CLI，不在 CI 中实现与本地不同的业务逻辑。
- `unit::time` benchmark 第一阶段只覆盖 roundtrip、leap second boundary、UT1 dependency、invalid inputs 四类场景。
- `docs/traceability/scope_to_contract.md` 中的 phase 路线由 `system-architect` 起草，但仅在 `contract_freeze` 后落盘。
- skill frontmatter 统一至少包含 `name`、`description`、`version`、`depends_on`、`tools`、`triggers`。
