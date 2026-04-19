# Harness Control Plane

本目录承载仓库的 harness 控制面，而不是业务实现。

当前内容：

- `orchestrator/`: 最小 task CLI 与 phase transition 规则
- `agents_runtime/`: Agents SDK v1 adapter、registry、allowlist、session/tracing helpers
- `config/`: tool allowlist、expert registry 与 CLI-only knowledge registry
- `schemas/`: 工件 JSON schema
- `templates/`: markdown / json 工件模板
- `session_policies/`: 会话隔离与允许上下文约束
- `runtime/`: 正式任务的控制面 runtime 状态与最小 artifacts；它不替代 `governance/records/` 中的人类可读治理记录，但从 `COLLAB-013` 起成为正式任务的必备记录
- `eval/`: control-plane / workflow 级评测夹具，与 `eval/domains/` 的产品级评测资产分层
- `tests/`: harness 轻量 Python 回归测试
