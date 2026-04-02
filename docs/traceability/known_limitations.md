# Known Limitations

本文件只记录当前已知且被接受的限制，不记录自动生成的覆盖率数字。

- Navigation / Prediction / Mission Planning 暂无业务实现。
- PPP / RD-POD 合同仍为占位版本。
- `tools/nav-toolchain-mcp benchmark` 当前只提供占位入口，不运行真实 benchmark。
- `nav-toolchain` 和 `traceability` 当前作为仓库内 CLI / 手动 stdio 工具维护，不走 Codex 默认自动加载。
