# Toolchain Overview

当前仓库把工程入口分成两类：

| 位置 | 角色 | 当前内容 |
| --- | --- | --- |
| `tools/` | 正式 repo-local CLI 本体 | `meson-cli`、`traceability-cli`、`governance-cli`、`site-cli`、`plantuml-cli` |
| `scripts/` | 轻量脚本、hook 安装器、验证器 | `validate_commit_message.py`、`install_commit_msg_hook.sh` |

约束：

- 大体量、频繁使用、依赖复杂的 Python 工具应进入 `tools/`
- `scripts/` 不再承载共享模块、测试目录或 CLI shim
- `scripts/meson-cli` 已删除；Meson 工具只通过 `tools/meson-cli` 入口调用
