# Decision Log

本文件记录已经冻结、并且会约束后续实现的工程决策。

## 2026-03-31 Initialization

- 公共时间模块归属 `product/src/unit/time`，命名空间固定为 `unit::time`。
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
- `docs/traceability/scope_to_contract.md` 中的 phase 路线由 `project-manager` 起草，但仅在 `contract_freeze` 后落盘；涉及架构方向时吸收 `architecture-expert` 结论。
- skill frontmatter 统一至少包含 `name`、`description`、`version`、`depends_on`、`tools`、`triggers`。

## 2026-04-02 Governance Role Split

- `system-architect` 角色拆分为 `project-manager` 与 `architecture-expert` 两个显式 skills。
- `project-manager` 成为唯一流程 owner，负责 intake、contract freeze 编排、状态推进、验收编排与里程碑管理。
- `architecture-expert` 作为被调度的专家角色，负责技术路线、模块边界、关键 trade-off、NFR 约束与跨模块依赖拓扑设计。
- 所有当前有效流程文档与 skill 上游关系统一迁移到新双角色模型；历史 backlog 和 activity log 记录保留原名称，不做追溯改写。

## 2026-04-02 Commit Message Relaxed Spec

- 仓库曾使用 header-only 的放宽版提交格式；该历史决策已被后续严格结构化规范替代。
- 仓库提交信息校验采用 repo-local `commit-msg` hook，入口固定为 `.githooks/commit-msg`。
- hook 安装命令固定为 `bash scripts/install_commit_msg_hook.sh`，通过 `core.hooksPath=.githooks` 激活。
- 提交规则只在 commit / publish / PR / release-finalization 阶段通过 `commit-message-policy` skill 加载，不进入 `AGENTS.md` 常驻上下文。

## 2026-04-03 Commit Message Structured Spec

- 仓库提交信息规范冻结为 `skills/commit-message-policy/` 下的严格结构化格式。
- 每个提交信息都必须包含 `Goal`、`Changes`、`Contracts`、`Traceability`、`Validation`、`Refs` 六个 section；无内容时必须填写 `None`。
- section 标签固定使用英文关键字加冒号，section 内容尽量使用中文。
- `scripts/validate_commit_message.py` 与 `.githooks/commit-msg` 必须按该严格格式拒绝缺失 section 或顺序错误的提交信息。

## 2026-04-02 Policy Skill Routing

- `AGENTS.md` 只承载全局协作治理和 policy 路由规则，不承载 task-specific 规则正文。
- `coding-style-rules`、`plantuml-architecture-styleguide`、`commit-message-policy` 统一作为按需加载的 policy skills。
- policy skill 的 `SKILL.md` 首屏必须可快速读完；长示例和展开说明下沉到 `references/`。
- 若规则存在配套脚本或执行入口，必须在 policy skill 的 `tools:` 和 `Enforced By` 中显式声明。

## 2026-04-02 Memory Layer Split

- `docs/memory/working/` 固定为当前执行快照入口，默认文件为 `current_focus.md`，采用单文件覆盖模式。
- `docs/memory/short_term/` 固定为当前迭代状态入口，默认文件为 `task_board.md` 与 `active_context.md`。
- `docs/traceability/` 固定为长期治理记忆、冻结约束与任务历史，不再承载当前 task blocker、当前任务状态或当前焦点。
- `docs/_generated/` 固定为 CI runtime 产物目录，不进入默认 agent 读取顺序，也不作为长期 RAG 输入。
- agents 的默认读取顺序固定为 `AGENTS.md -> working memory -> short-term memory -> known_limitations -> scope_to_contract -> decision_log / agent_activity_log (按需) -> relevant contracts -> relevant skills`。

## 2026-04-03 Harness Product Split

- 仓库结构冻结为根目录治理层 + `harness/` 控制面 + `product/` 产品面。
- `project-manager` 继续作为唯一流程 owner；`architecture-expert` 只在被调度时给出架构冻结结论。
- 根目录 CLI 入口保持稳定，即使真实源码与测试迁移到 `product/`。
- `harness/runtime/` 只保存可重建运行态，不替代 `docs/memory/` 或 `docs/traceability/`。

## 2026-04-03 Codex Project Default Layout

- 仓库默认 Codex 入口冻结为根 `AGENTS.md` + 项目 `.agents/skills` + repo-local CLI。
- 根 `skills/` 继续作为技能内容维护目录，`.agents/skills` 只承担项目级发现职责。
- 停止维护 plugin bundle、`.codex-plugin/`、`.mcp.template.json` 和本地 plugin 安装脚本作为默认仓库入口。
- 仓库当前不引入项目级 `.codex/config.toml`；只有在确实需要 trusted-project overrides 或项目级 Codex 配置时再单独引入。

## 2026-04-03 Repo-Local CLI First Tooling

- `tools/nav-toolchain-cli/` 与 `tools/traceability-cli/` 成为仓库内唯一受支持的工程工具入口；原 `*-mcp` 目录、`server.py` 包装和 `scripts/run_uv_mcp.sh` 不再维护。
- side-effectful CLI 子命令必须至少提供 `--dry-run` 预演能力；写报告或生成产物的入口应提供显式确认开关。
- 顶层与子命令 `--help` 必须包含可直接复制的 `Examples`，错误输出必须带可执行示例或下一步提示。
- `traceability-cli` 的 `status` / `query-clause` 默认只读取现有产物；需要重生成时通过 `--refresh` 显式触发。

## 2026-04-07 Agents SDK Harness Adapter V1

- `harness/` 新增 Agents SDK-oriented runtime adapter，但现有 phase 状态机与 schema 仍是规范源；adapter 必须复用而不是复制 transition 逻辑。
- v1 自动化拓扑明确包含 `architecture_expert_agent`，且仅在 `contract_freeze` 命中架构/NFR/层边界条件时由 PM handoff。
- curator 固定为 `project-manager` 内嵌步骤；knowledge patch proposal 必须 human-in-the-loop 审批后才能写回 repo 规范源。
- resume 只允许在相同 session backend 路径与凭据下继续；跨环境静默恢复必须拒绝。
- tool wrapper allowlist 与 expert-contract registry 必须作为单一配置源，供 guardrail、adapter 与单元测试共用。

## 2026-04-07 CLI-Only Obsidian Expert Bridge And PPP Family V1

- `expert-system` Obsidian vault 只能通过 repo-local `toolchain_cli.py knowledge ...` wrapper 访问；不得直接读取或写入 vault 文档。
- fresh expert knowledge lookup 必须要求 Obsidian app 已在本机运行；若运行门禁未打开，harness 直接阻断而不是绕过或静默降级。
- `pppar_expert_agent` 的 session 命名空间冻结为 `expert/<task_id>/pppar_expert_agent`；不得与 `coding/`、`testing/`、`eval/` 会话复用或交叉 resume。
- `contracts/ppp_family.contract.md` 从占位版升级为 v1：PRIDE-PPPAR 仍是权威实现源，Obsidian supplemental knowledge 只能增强解释，不能覆盖 PRIDE 证据。

## 2026-04-07 Harness Governance Hard Cutover

- 从 `COLLAB-013` 起，正式任务必须保留 `harness/runtime/tasks/<task_id>/` 下的最小控制面记录，至少包括 `task_state.json` 与 `events.jsonl`。
- `docs/memory/*`、`docs/traceability/agent_activity_log.md`、`docs/traceability/task_archive.md` 继续保留为人类可读治理文档，但默认视为 `harness_cli` 同步出来的镜像，而不是独立主状态机。
- 新任务启动默认使用 `python3 harness/orchestrator/harness_cli.py pm-workflow`；不需要 expert dispatch 的一般任务使用 `--skip-dispatch`，而不是绕开 harness。
- phase 推进固定通过 `advance` / `pm-workflow`，acceptance 固定通过 `close-task` / `archive-task`，治理漂移修复固定通过 `sync-governance`。

## 2026-04-07 Prompt Doc Progressive Disclosure

- `AGENTS.md`、`skills/project-manager/SKILL.md`、`docs/architecture/agent-collaboration.md` 只保留主路径最小入口信息，默认控制在 100 行内。
- detailed command cookbook 与 role-specific load routing 下沉到 `skills/project-manager/references/`，入口层不再重复维护完整 SOP。
- 默认读链按角色分流：全局入口只保留最小共识，`decision_log.md`、`agent_activity_log.md`、`agent-collaboration.md` 等长文档改为 conditional load。
- `scripts/check_quality.py` 负责阻断 prompt docs 回退到超长首屏或重复 SOP 的状态。
