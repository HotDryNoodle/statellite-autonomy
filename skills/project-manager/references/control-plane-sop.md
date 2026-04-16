# PM Control Plane SOP

Use these repo-local command templates for official task flow.

## Start A General Task

```bash
python3 harness/orchestrator/harness_cli.py pm-workflow \
  --task-id <task-id> \
  --goal "<goal>" \
  --contract <contract-path> \
  --skip-dispatch
```

## Start A Task That Needs Expert Context

```bash
python3 harness/orchestrator/harness_cli.py pm-workflow \
  --task-id <task-id> \
  --goal "<goal>" \
  --contract <contract-path> \
  --agent <expert-agent> \
  --knowledge-query "<query>"
```

## Advance A Task

```bash
python3 harness/orchestrator/harness_cli.py advance \
  --task-id <task-id> \
  --phase <verification|traceability|acceptance> \
  --owner <agent>
```

## Resume Expert Context

```bash
python3 harness/orchestrator/harness_cli.py resume-agent \
  --task-id <task-id> \
  --agent <expert-agent>
```

## Repair Governance Drift

```bash
python3 harness/orchestrator/harness_cli.py sync-governance --task-id <task-id>
```

## Close And Archive

```bash
python3 harness/orchestrator/harness_cli.py close-task \
  --task-id <task-id> \
  --acceptance-summary "<summary>" \
  --archive
```

