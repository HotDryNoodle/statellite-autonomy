# Known Limitations

## Accepted Limitations

- Navigation / Prediction / Mission Planning 暂无业务实现。
- PPP / RD-POD 合同仍为占位版本。
- `nav-toolchain` 和 `traceability` 当前作为仓库内 CLI / 手动 stdio 工具维护，不走 Codex 默认自动加载。

## Open Risks

- `docs/traceability/` 向 `docs/memory/` 的 current-state 迁移刚完成，后续新增 task 若仍回写旧入口会导致状态漂移。
