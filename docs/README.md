# Docs Index

`docs/` 只保留阅读层内容，不承载权威 blueprint、policy 或 governance record 主副本。

## Read Here

- `guides/`
  - 人类阅读型流程说明和边界导览。
- `toolchain/`
  - build / test / traceability / benchmark 入口说明。
- `plugin-installation.md`
  - 本地集成说明。
- `backlog.md`
  - 对当前工作面板和归档的入口提示。

## Canonical Asset Roots

- `contracts/`
- `architecture/blueprints/`
- `governance/policies/`
- `governance/records/`
- `eval/domains/`
- `harness/runtime/`
- `harness/eval/`

## Project static site (read-only aggregate)

面向开发者的只读静态站点由 **`site/`**（MkDocs）生成，命令入口固定为 `tools/site-cli/` 的 `statellite-site`；设计与命令见根目录 `README.md` 中的 **Project Site** 小节与 `site/README.md`。

本仓库**不再**使用基于 Node/VitePress 的 `docs/` 内嵌站点；若文档或 CI 仍提及 VitePress、`.vitepress` 或 `docs/.vitepress/dist`，应视为过时并改为指向 `site/`。
