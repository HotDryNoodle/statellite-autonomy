# Known Limitations

## Accepted Limitations

- Navigation / Prediction / Mission Planning 暂无业务实现。
- PPP / RD-POD 合同仍为占位版本。
- `nav-toolchain` 和 `traceability` 当前作为仓库内 CLI / 手动 stdio 工具维护，不走 Codex 默认自动加载。
- harness 当前只实现最小 orchestrator CLI 与工件 schema，不包含自动多 agent 执行引擎。

## Open Risks

- `docs/traceability/` 向 `docs/memory/` 的 current-state 迁移刚完成，后续新增 task 若仍回写旧入口会导致状态漂移。
- `product/` 路径迁移后，若后续 skill / script / doc 继续引用旧 `src/`、`tests/` 路径，会导致治理与实现重新漂移。
