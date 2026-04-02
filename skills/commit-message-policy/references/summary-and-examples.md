# Commit Message Policy References

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
- backlog: updated|n/a
- activity_log: updated|n/a
- decision_log: updated|n/a

Validation:
- ...

Refs: ...
```

## 通过示例

```text
docs: add plugin installation troubleshooting notes
```

```text
trace(collaboration,skills): migrate orchestration owner to project-manager

Goal:
- align workflow roles with new governance

Changes:
- update AGENTS and collaboration docs

Refs: COLLAB-003
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
