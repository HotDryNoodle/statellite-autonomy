# Commit Message Policy References

## 规则展开

- 第一行必须匹配 `<type>(<scope>): <summary>`
- `type` 只能使用 `feat|fix|refactor|docs|test|build|ci|chore|perf|trace`
- `scope` 可选；若存在，只能使用小写字母、数字、逗号、连字符
- `summary` 长度限制为 `1..72`
- header 之后必须按顺序包含 `Goal`、`Changes`、`Contracts`、`Traceability`、`Validation`、`Refs`
- 每个 section 都必须存在；没有内容时必须显式写 `None`
- section 标签固定使用英文关键字加冒号
- section 内容尽量使用中文
- 每个 section 至少保留一行非空内容

## 推荐模板

```text
<type>(<scope>): <summary>

Goal:
- ...

Changes:
- ...

Contracts:
- affected: ...
- behavior-change: yes|no

Traceability:
- task_id: ...
- current_focus: updated|n/a
- task_board: updated|n/a
- active_context: updated|n/a
- activity_log: updated|n/a
- decision_log: updated|n/a

Validation:
- ...

Refs:
- ...
```

## 通过示例

```text
trace(commit-policy): 严格化提交信息模板

Goal:
- 收紧 commit message 校验，要求保留关键治理字段。

Changes:
- 更新 validator、规范文档和 policy 示例。

Contracts:
- affected: contracts/layer_boundary.contract.md
- behavior-change: no

Traceability:
- task_id: COLLAB-007
- current_focus: updated
- task_board: updated
- active_context: updated
- activity_log: updated
- decision_log: updated

Validation:
- python3 scripts/validate_commit_message.py /tmp/message.txt

Refs:
- COLLAB-007
```

## 不通过示例

```text
unknown(scope): this should fail
```

原因：`type` 不在白名单。

```text
fix(scope) missing colon
```

原因：缺少 `: ` 分隔符。

```text
docs(commit-policy): 只写标题
```

原因：缺少必填 section。
