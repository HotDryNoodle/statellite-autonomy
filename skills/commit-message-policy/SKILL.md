---
name: commit-message-policy
description: Commit / publish policy skill。用于在 commit、PR、发布封板等阶段加载本仓库的严格结构化 commit message 约束，并指向对应 hook、校验脚本和安装入口。
version: 1.0.0
depends_on: []
tools:
  - skills/commit-message-policy/references/summary-and-examples.md
  - .githooks/commit-msg
  - scripts/validate_commit_message.py
  - scripts/install_commit_msg_hook.sh
triggers:
  - commit
  - publish
  - pull-request
---

# Commit Message Policy

## TL;DR

- 仅在 commit / publish / PR / 封板阶段加载。
- 第一行必须匹配 `<type>(<scope>): <summary>`，其中 `scope` 可选。
- 必须按顺序包含 `Goal`、`Changes`、`Contracts`、`Traceability`、`Validation`、`Refs` 六个 section。
- 校验入口：`.githooks/commit-msg` 和 `scripts/validate_commit_message.py`
- 安装入口：`bash scripts/install_commit_msg_hook.sh`

## Load When

- 需要创建 git commit
- 需要整理提交信息用于 PR 或发布
- 需要检查提交信息是否符合仓库规范

## Must Follow

- `type` 只能使用 `feat|fix|refactor|docs|test|build|ci|chore|perf|trace`
- `summary` 长度限制为 `1..72`
- 缺失 section 时必须显式填写 `None`
- section 内容尽量使用中文
- 详细模板与展开规则以 `references/summary-and-examples.md` 为准

## Enforced By

- Hook: `.githooks/commit-msg`
- Validator: `python3 scripts/validate_commit_message.py <message-file>`
- Install: `bash scripts/install_commit_msg_hook.sh`

## References

- `references/summary-and-examples.md`
