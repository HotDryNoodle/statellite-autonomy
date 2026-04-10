@page requirements_eval_governance_contract EvalGovernance Contract
@ingroup requirements

# EvalGovernance Contract

## 1. 目标

冻结本项目 Eval Owner 的职责边界、`eval/` 资产治理协议、baseline 生命周期、结果裁决语义，以及评测结果与验收证据的绑定规则。

## 2. 角色定位

- Eval Owner 负责评测协议、场景资产治理、baseline 冻结、结果裁决与验收证据输出。
- Eval Owner 不负责系统架构路线、算法实现修改或 PM 优先级决策。

## 3. 数据输入（Inputs）

| 名称 | 来源 | 说明 |
| --- | --- | --- |
| Domain Manifest | `eval/domains/<domain>/manifest.json` | domain 级 owner、默认 baseline、变更记录与执行模式 |
| Scenario Definition | `eval/domains/<domain>/scenarios/*.json` | 场景版本、合同绑定、真值来源与执行配置 |
| Baseline Definition | `eval/domains/<domain>/baselines/*.json` | 阈值、统计口径、审批状态与重标定策略 |
| Eval Report | `eval/reports/*.json` | 标准化 verdict、风险、归因与证据摘要 |
| Contract Verify Refs | `contracts/*.contract.md` | 被评测结果绑定的 verify 条款 |

## 4. 数据处理与设计约束（Contracts）

### 4.1 Eval Owner 边界

@contract{EvalGovernance_4_1}

Contract：

- Eval Owner 负责维护评测协议、场景资产分层、baseline 生命周期与结果裁决。
- Eval Owner 必须输出可归档的 verdict / risk / attribution 结论。
- Eval Owner 只负责生成和维护评测资产与评测结论，不直接主写 `scope_to_contract`、`decision_log`、`known_limitations`、`task_archive` 等长期治理文档；这些文档只接收其 report 作为输入证据。
- Eval Owner 不得代替 `architecture-expert` 冻结系统架构，不得代替 `coding-skill` / `testing-skill` 修改算法或测试实现，不得代替 `project-manager` 做优先级与最终验收决策。

### 4.2 `eval/` 资产治理

@contract{EvalGovernance_4_2}

Contract：

- 产品/算法评测资产必须按 `eval/domains/<domain>/manifest.json`、`scenarios/`、`baselines/` 分层组织。
- 每个 scenario 至少必须声明 `scenario_id`、`scenario_version`、`domain`、`verify_refs`、`contract_refs`、`truth_source_refs` 与 `runner_adapter`。
- 每个 baseline 至少必须声明 `baseline_id`、`baseline_version`、阈值/统计口径、真值来源、审批状态与重标定策略。
- 不允许存在未被 domain manifest 索引、且无人负责的孤儿 scenario / baseline 资产。

### 4.3 Baseline 冻结与重标定

@contract{EvalGovernance_4_3}

Contract：

- baseline 默认视为冻结版本，只有在数据、统计口径、真值来源或执行协议发生实质变化时才允许重标定。
- 重标定必须由 Eval Owner 起草 proposal，并明确影响的 scenario、verify、baseline version 与变更原因。
- 重标定生效前必须完成 PM 与对应领域专家双签；未审批 baseline 不得作为 release / acceptance 的签字依据。

### 4.4 统一裁决语义

@contract{EvalGovernance_4_4}

Contract：

- 统一评测报告必须输出 `verdict`、`risk_level`、`attribution`、`scenario_versions`、`baseline_version`、`verify_refs`、`artifact_paths` 与 `summary_for_acceptance`。
- `verdict` 只允许 `pass`、`fail`、`blocked` 三态；`blocked` 表示资产、数据或工具链条件不足，禁止伪装为 `pass` 或 `fail`。
- `attribution` 至少覆盖 `data_issue`、`config_drift`、`algorithm_regression`、`toolchain_failure` 四类归因。
- report 必须能把失败或阻断回溯到具体 scenario、baseline version 与合同 verify 条款。

### 4.5 验收签字证据

@contract{EvalGovernance_4_5}

Contract：

- release / acceptance 所需的评测证据必须采用标准化 Eval report，而不是仅保留原始数值或控制台输出。
- `project-manager` 保留最终签字权，但没有 Eval Owner 的标准化报告时不得形成“可签字”验收结论。
- Eval report 必须作为 traceability / acceptance 可引用的稳定产物路径保存。
- `traceability-manager` 负责把 Eval report 绑定到 contract verify 条款、runtime evidence 和治理镜像；`traceability-manager` 不定义 baseline、不过问阈值口径，也不直接裁决 pass/fail。

## 5. 测试要求（verify）

@verify{EvalGovernance_5_1}

- 目的：验证 `eval/` domain/scenario/baseline 资产满足统一 schema 与索引约束。
- 关联合同：`@contract{EvalGovernance_4_2}`

@verify{EvalGovernance_5_2}

- 目的：验证标准化 Eval report 会输出 verdict、风险、归因、版本和 verify 绑定信息。
- 关联合同：`@contract{EvalGovernance_4_4}` `@contract{EvalGovernance_4_5}`

@verify{EvalGovernance_5_3}

- 目的：验证 baseline 重标定需要 Eval proposal 与 PM/领域专家双签元数据。
- 关联合同：`@contract{EvalGovernance_4_3}`

## 附录A：设计约束表

| ClauseId | 说明 |
| --- | --- |
| `@contract{EvalGovernance_4_1}` | Eval Owner 边界 |
| `@contract{EvalGovernance_4_2}` | `eval/` 资产治理 |
| `@contract{EvalGovernance_4_3}` | Baseline 冻结与重标定 |
| `@contract{EvalGovernance_4_4}` | 统一裁决语义 |
| `@contract{EvalGovernance_4_5}` | 验收签字证据 |

## 附录B：测试验证表

| verify-ID | 说明 |
| --- | --- |
| `@verify{EvalGovernance_5_1}` | 资产 schema 与索引 |
| `@verify{EvalGovernance_5_2}` | 标准化 Eval report |
| `@verify{EvalGovernance_5_3}` | baseline 重标定审批 |
