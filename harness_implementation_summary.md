# Harness 实施方案总结（结合当前 Agent 体系与推荐实现方式）

## 1. 总体目标

当前项目的最终目标不是单纯构建一组 agent，而是：

```text
利用 Codex plugin / subagents / skills / MCP / contracts / harness 工程，持续产出、验证并演化你的导航相关二进制程序。
```

因此，整个实施方案应分成两层理解：

### 上层：AI 开发与验证系统
包括：
- Codex plugin
- subagents
- skills
- MCP
- harness orchestration
- contracts / handoff / task brief / feedback / traceability

### 下层：真实软件工程与二进制产物
包括：
- `src/`
- `tests/`
- build system
- benchmark harness
- binary / library / deployable artifacts

结论是：

- agents 不是最终产品
- harness 不是最终产品
- 它们是“开发系统”
- 最终产品仍然是你的可编译、可测试、可部署的导航软件二进制

---

## 2. 项目阶段与系统边界

### 2.1 顶层蓝图：三层架构
整个项目面向 **卫星自主任务规划**，长期采用三层架构：

- **Navigation**：卫星现在在哪里
- **Prediction**：卫星未来在哪里
- **Mission Planning**：什么时候执行任务、如何安排任务

### 2.2 当前阶段：只闭环 Navigation
当前第一阶段不追求三层都实现，而是：

- 先闭环 **Navigation**
- Prediction 只做 handoff 接口占位
- Mission Planning 只做接口与 schema 占位

### 2.3 当前 Navigation 求解家族
当前收敛为两个求解家族：

- **PPP family**
  - `PPP-float`
  - `PPP-AR`
- **RD-POD family`

说明：
- SPP 不再单独组织为一个家族
- 当前 PPP 体系聚焦 PPP-float / PPP-AR

---

## 3. Agent 体系：当前第一阶段的完整集合

## 3.1 P0 核心角色
这些角色会直接参与第一阶段高频开发闭环：

- `system-architect`
- `pppar-expert`
- `rdpod-analyst`
- `coding-skill`
- `testing-skill`
- `benchmark-evaluator`
- `OrbitDataMCP`

## 3.2 P1 治理与工具链
这些不一定最先成为主线，但应尽早补齐：

- `traceability-manager`
- `NavToolchainMCP`

## 3.3 P2 未来占位
这些角色先占住边界，不做重实现：

- `prediction-designer`
- `mission-planning-designer`

---

## 4. Codex plugin / subagent / harness 的定位关系

### 4.1 Codex plugin 的定位
Codex plugin 不是最终业务程序，而是一个：

```text
被 Codex 原生加载的能力包（capability bundle）
```

它内部可以包含：
- 多个 agent
- skills
- MCP servers
- workflows
- tool integrations

对这个项目来说，plugin 的意义是：

```text
把多 agent 开发系统打包成 Codex 可调用的能力扩展层
```

### 4.2 harness 的定位
harness 不是 plugin 的替代品，而是 plugin 内部的**工程实现骨架**。

也就是：

- plugin 决定“可加载、可扩展、可调用”
- harness 决定“怎么 orchestrate subagents、怎么做 handoff、怎么做 feedback、怎么跑 build/test/benchmark”

### 4.3 subagent 模式的判断
采用：

- `project-manager`
- `constraint-expert`
- `execution-agent`
- `testing-agent`
- `benchmark-agent`

这种 **subagent + 不同会话隔离 + handoff 衔接** 的方式，从 harness 工程实现角度是可行的，而且很适合当前项目。

---

## 5. harness 的推荐实现原则

整个 harness 不应仅仅是“多个 agent 对话”，而应被实现成一个：

```text
受控的、工件驱动的、多会话状态机
```

### 5.1 核心原则
- subagent 必须会话隔离
- 任务推进必须通过显式工件
- feedback 必须结构化
- orchestrator 必须是唯一总控
- build/test/benchmark 必须统一执行入口
- traceability 必须可回放、可追踪

---

## 6. 推荐的 harness 五层结构

### Layer 1: Orchestrator 层
唯一总控，对应：
- `project-manager`
- 或当前体系中的 `system-architect`

职责：
- 接收目标
- 拆任务
- 选择 subagent
- 生成 handoff
- 收集反馈
- 做路由、重试、升级、合并决策

### Layer 2: Session Isolation 层
每个 subagent 在单独 session 中运行。

每个 session 只暴露必要信息：
- task brief
- scope
- relevant contracts
- relevant context refs
- allowed tools
- feedback summary

作用：
- 防止上下文污染
- 限定 agent 作用域
- 方便调试与复盘

### Layer 3: Artifact 层
任务不靠聊天推进，而靠工件推进。

推荐至少保留：
- `task_brief.md`
- `contract.md`
- `handoff.json`
- `execution_report.json`
- `review_feedback.json`
- `decision_log.md`

### Layer 4: Execution Surface 层
由 MCP 暴露工具链能力。

这里的核心是：
- `OrbitDataMCP`：负责数据与场景
- `NavToolchainMCP`：负责工程执行入口

### Layer 5: Feedback Loop 层
反馈应采用：

```text
agent A -> structured feedback -> orchestrator -> summarized handoff -> agent B
```

而不是 agent 之间自由对话。

---

## 7. 当前项目的角色映射

结合你当前收敛后的 agent 体系，可以映射成下面这样：

### 总控层
- `system-architect`
  - 在 harness 中承担 `project-manager / orchestrator` 角色

### 领域层
- `pppar-expert`
  - PPP family 强专家
- `rdpod-analyst`
  - RD-POD 研究型 / 设计型支撑
- `prediction-designer`
  - Prediction 层占位设计器
- `mission-planning-designer`
  - Mission Planning 层占位设计器

### 执行层
- `coding-skill`
  - 对应 `execution-agent`
- `testing-skill`
  - 对应 `testing-agent`

### 评测与治理层
- `benchmark-evaluator`
  - 对应 `benchmark-agent`
- `traceability-manager`
  - 负责 requirement -> contract -> code -> tests -> benchmark 的追踪链

### MCP 层
- `OrbitDataMCP`
  - 提供 EOP / GNSS / STK / reference orbit / benchmark scenario 等数据
- `NavToolchainMCP`
  - 提供 build / test / benchmark / artifacts / logs 等统一执行入口

---

## 8. 推荐的工件驱动协作模式

### 8.1 task brief
任务起点，由 orchestrator 生成。

应包含：
- task id
- parent task
- goal
- scope
- relevant contracts
- success criteria
- allowed tools
- input refs
- output expectation

### 8.2 contract
是各 subagent 必须遵守的功能与边界约束。

当前第一阶段建议优先维护的核心 contract：
- `navigation.contract.md`
- `ppp_family.contract.md`
- `rdpod_family.contract.md`
- `state_handoff_navigation_to_prediction.contract.md`

### 8.3 handoff
是 orchestrator 在 agent 间转交任务时的中间说明。

应明确：
- 当前上下文摘要
- 子任务目标
- 必须遵守的 contract
- 上一轮反馈
- 风险与 blocker

### 8.4 feedback
推荐固定为结构化反馈，而非自由语言往返。

建议统一字段：
- `summary`
- `issues_found`
- `contract_violations`
- `risks`
- `confidence`
- `suggested_next_owner`
- `recommended_actions`

### 8.5 execution report
execution / testing / benchmark 结束后，都应产出报告。

例如：
- 改了哪些文件
- 哪些测试通过/失败
- benchmark 结果如何
- 是否满足 success criteria

---

## 9. 推荐的反馈机制设计

你特别强调要增加 agent 之间的反馈机制。建议采用下面三类反馈：

### 9.1 Review Feedback
例如：
- `constraint-expert` 对 `execution-agent` 的审查
- `pppar-expert` 对 PPP 代码实现的审查

作用：
- 检查 contract 是否被违反
- 检查方案是否满足约束
- 决定是否允许进入下一阶段

### 9.2 Clarification Feedback
例如：
- `execution-agent` 发现 task brief 缺少必要条件
- `testing-agent` 发现 contract 中测试口径不完整

作用：
- 不让 agent 盲目猜测
- 把问题回抛给 orchestrator 处理

### 9.3 Benchmark Feedback
例如：
- `benchmark-evaluator` 基于数据集结果，对当前实现给出达标 / 不达标结论

作用：
- 把系统级性能反馈给总控
- 决定是否进入下一轮修复

### 9.4 反馈机制的关键原则
- 反馈必须通过 orchestrator 转发
- 不建议 agent 之间自由持续对话
- 应设置往返轮数上限
- 超过上限后升级给 orchestrator 做决策

---

## 10. Traceability 与知识库的关系

### 10.1 traceability-manager 的作用
在多 agent 开发中，traceability-manager 负责维护：

```text
需求 -> contract -> 实现 -> 测试 -> benchmark -> 决策
```

它应维护至少这些文档：
- `requirement_to_contract.md`
- `contract_to_code.md`
- `code_to_tests.md`
- `decision_log.md`
- `known_limitations.md`

### 10.2 Obsidian 知识库的作用
如果你未来为 expert agents 外接本地 Obsidian 知识库，则建议它承担：
- 外部资料层
- 审核提炼层
- 项目决策层

并通过 MCP 提供受控访问。

关键不是“全量读笔记”，而是：
- 按 metadata 过滤
- 按 agent role 提供视图
- 区分 confidence / status
- 区分 source / concept / model / design / validation

这会和 `traceability-manager`、`system-architect`、`pppar-expert`、`rdpod-analyst` 形成互补关系。

---

## 11. 面向二进制程序产出的工程原则

因为你的最终目标是产出真实二进制程序，所以整个方案必须遵守下面几条：

### 原则 1
核心业务逻辑必须沉到真实源码中，而不是停留在 prompt / skill / MCP 中。

### 原则 2
harness / plugin / agents 只负责：
- 组织开发
- 调用工具链
- 生成实现
- 跑测试与评测
- 维护治理工件

### 原则 3
二进制程序的 build / test / deploy 流程，必须在离开 Codex 后仍能独立运行。

### 原则 4
NavToolchainMCP 应围绕“稳定产出 binary”来设计，而不是做成一个聊天工具。

---

## 12. 推荐的目录结构（整合版）

```text
satellite-autonomy-plugin/
├── contracts/
│   ├── layer_boundary.contract.md
│   ├── navigation.contract.md
│   ├── prediction.contract.md
│   ├── mission_planning.contract.md
│   ├── ppp_family.contract.md
│   ├── rdpod_family.contract.md
│   └── state_handoff_navigation_to_prediction.contract.md
│
├── skills/
│   ├── system-architect/
│   │   └── SKILL.md
│   ├── pppar-expert/
│   │   └── SKILL.md
│   ├── rdpod-analyst/
│   │   └── SKILL.md
│   ├── coding-skill/
│   │   └── SKILL.md
│   ├── testing-skill/
│   │   └── SKILL.md
│   ├── benchmark-evaluator/
│   │   └── SKILL.md
│   ├── traceability-manager/
│   │   └── SKILL.md
│   ├── prediction-designer/
│   │   └── SKILL.md
│   └── mission-planning-designer/
│       └── SKILL.md
│
├── harness/
│   ├── orchestrator/
│   ├── session_policies/
│   ├── handoffs/
│   ├── task_graph/
│   ├── feedback/
│   └── schemas/
│
├── mcp/
│   ├── orbit-data-mcp/
│   └── nav-toolchain-mcp/
│
├── docs/
│   ├── traceability/
│   └── toolchain/
│
├── eval/
│   ├── scenarios/
│   ├── baselines/
│   └── reports/
│
└── product/
    ├── src/
    │   ├── navigation/
    │   │   ├── ppp/
    │   │   └── rdpod/
    │   ├── prediction/
    │   └── mission_planning/
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   └── regression/
    └── build/
```

说明：
- `plugin/harness` 管开发智能体系统
- `product/` 管真实软件工程和最终二进制
- 两者分层明确，避免角色混淆

---

## 13. 第一阶段的推荐开发流程（整合版）

### Step 1：需求归约
由 `system-architect` 执行：
- 识别任务属于 Navigation 哪部分
- 判断是否影响 PPP family / RD-POD family / shared interface
- 生成 `task_brief`

### Step 2：方案分析
- PPP 相关问题交给 `pppar-expert`
- RD-POD 相关问题交给 `rdpod-analyst`
- 必要时由 `traceability-manager` 补追踪上下文

### Step 3：contract 收敛
由 `system-architect` 汇总并冻结相关 contract。

### Step 4：实现
由 `coding-skill` 在独立 session 中实现。
必要时通过 `NavToolchainMCP` 做 build。

### Step 5：测试
由 `testing-skill` 在独立 session 中执行 unit / integration / regression。
必要时通过 `NavToolchainMCP` 跑测试。

### Step 6：评测
由 `benchmark-evaluator` 基于 `OrbitDataMCP` 和 `NavToolchainMCP` 运行 benchmark，生成评测报告。

### Step 7：治理与归档
由 `traceability-manager` 更新：
- requirement -> contract
- contract -> code
- code -> tests
- benchmark -> decision

### Step 8：总控裁决
由 `system-architect` 结合所有工件决定：
- merge
- revise
- reject
- backlog

---

## 14. 最小可实现版本（MVP）

如果你现在就要开始搭 harness，建议先做一个最小版本，而不是一次性做完整平台。

### MVP 角色
- `system-architect` / `project-manager`
- `pppar-expert`
- `rdpod-analyst`
- `coding-skill`
- `testing-skill`
- `benchmark-evaluator`

### MVP 工件
- `task_brief.md`
- `contract.md`
- `handoff.json`
- `execution_report.json`
- `review_feedback.json`
- `decision_log.md`

### MVP MCP
- `OrbitDataMCP`
- `NavToolchainMCP`（轻量版）

### MVP 能力
- 独立 session 运行
- orchestrator 路由 subagent
- 至少一轮 review-feedback
- build/test/benchmark 统一入口
- trace 可回放

---

## 15. 最终总结

把上面的方案压缩成一句话，就是：

```text
以 Codex plugin 为能力打包层，以 harness 为多会话 subagent 编排骨架，以 contract / handoff / task brief / structured feedback 为工件衔接，以 OrbitDataMCP 和 NavToolchainMCP 分别承担数据入口和工程执行入口，在第一阶段先闭环 Navigation（PPP-float / PPP-AR + RD-POD），持续产出并验证真实可部署的二进制程序，同时为 Prediction 和 Mission Planning 预留接口边界。
```

这是当前最完整、最可实施、也最符合你项目实际情况的一版实施方案。

