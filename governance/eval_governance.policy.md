# Eval Governance Policy

冻结 Eval Owner 的职责边界、`eval/` 资产治理协议、baseline 生命周期、结果裁决语义，以及评测结果与验收证据的绑定规则。本文件是治理 policy，不参与 `ClauseId` 追溯。

## Inputs


| Name                | Source                                   | Notes                                |
| ------------------- | ---------------------------------------- | ------------------------------------ |
| Domain Manifest     | `eval/domains/<domain>/manifest.json`    | domain 级 owner、默认 baseline、变更记录与执行模式 |
| Scenario Definition | `eval/domains/<domain>/scenarios/*.json` | 场景版本、product contract 绑定、真值来源与执行配置   |
| Baseline Definition | `eval/domains/<domain>/baselines/*.json` | 阈值、统计口径、审批状态与重标定策略                   |
| Eval Report         | `eval/reports/*.json`                    | 标准化 verdict、风险、归因与证据摘要               |
| Product Verify Refs | `contracts/*.contract.md`                | 被评测结果绑定的 product verify 条款           |


## Policy Rules

### Eval Owner Boundary

- Eval Owner 负责维护评测协议、场景资产分层、baseline 生命周期与结果裁决。
- Eval Owner 必须输出可归档的 verdict / risk / attribution 结论。
- Eval Owner 只负责生成和维护评测资产与评测结论，不直接主写 `scope_to_spec`、`decision_log`、`known_limitations`、`task_archive` 等长期治理文档；这些文档只接收其 report 作为输入证据。
- Eval Owner 不得代替 `architecture-expert` 冻结系统架构，不得代替 `coding-skill` / `testing-skill` 修改算法或测试实现，不得代替 `project-manager` 做优先级与最终验收决策。

### Eval Asset Governance

- 产品/算法评测资产必须按 `eval/domains/<domain>/manifest.json`、`scenarios/`、`baselines/` 分层组织。
- 每个 scenario 至少必须声明 `scenario_id`、`scenario_version`、`domain`、`verify_refs`、`contract_refs`、`truth_source_refs` 与 `runner_adapter`。
- 每个 baseline 至少必须声明 `baseline_id`、`baseline_version`、阈值/统计口径、真值来源、审批状态与重标定策略。
- 不允许存在未被 domain manifest 索引、且无人负责的孤儿 scenario / baseline 资产。

### Baseline Recalibration

- baseline 默认视为冻结版本，只有在数据、统计口径、真值来源或执行协议发生实质变化时才允许重标定。
- 重标定必须由 Eval Owner 起草 proposal，并明确影响的 scenario、verify、baseline version 与变更原因。
- 重标定生效前必须完成 PM 与对应领域专家双签；未审批 baseline 不得作为 release / acceptance 的签字依据。

### Verdict Semantics

- 统一评测报告必须输出 `verdict`、`risk_level`、`attribution`、`scenario_versions`、`baseline_version`、`verify_refs`、`artifact_paths` 与 `summary_for_acceptance`。
- `verdict` 只允许 `pass`、`fail`、`blocked` 三态；`blocked` 表示资产、数据或工具链条件不足，禁止伪装为 `pass` 或 `fail`。
- `attribution` 至少覆盖 `data_issue`、`config_drift`、`algorithm_regression`、`toolchain_failure` 四类归因。
- report 必须能把失败或阻断回溯到具体 scenario、baseline version 与 product verify 条款。

### Acceptance Evidence

- release / acceptance 所需的评测证据必须采用标准化 Eval report，而不是仅保留原始数值或控制台输出。
- `project-manager` 保留最终签字权，但没有 Eval Owner 的标准化报告时不得形成“可签字”验收结论。
- Eval report 必须作为 traceability / acceptance 可引用的稳定产物路径保存。
- `traceability-manager` 负责把 Eval report 绑定到 product verify 条款、runtime evidence 和治理镜像；`traceability-manager` 不定义 baseline、不过问阈值口径，也不直接裁决 pass/fail。

## Stable References


| Policy Ref                                                    | Meaning         |
| ------------------------------------------------------------- | --------------- |
| `governance/eval_governance.policy.md#eval-owner-boundary`    | Eval Owner 边界   |
| `governance/eval_governance.policy.md#eval-asset-governance`  | `eval/` 资产治理    |
| `governance/eval_governance.policy.md#baseline-recalibration` | Baseline 冻结与重标定 |
| `governance/eval_governance.policy.md#verdict-semantics`      | 统一裁决语义          |
| `governance/eval_governance.policy.md#acceptance-evidence`    | 验收签字证据          |
