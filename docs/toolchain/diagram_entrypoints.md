# Diagram Entrypoints

- `uv run --group plantuml --no-default-groups plantuml-cli lint --input <file.puml>`
- `uv run --group plantuml --no-default-groups plantuml-cli render --input <file.puml> --output <file.svg>`
- `PLANTUML_SERVER_URL=http://127.0.0.1:8080 uv run --group plantuml --no-default-groups plantuml-cli lint --input <file.puml>`

说明：

- `plantuml-cli` 只支持 server-based `lint` / `render`
- 若未显式指定 `PLANTUML_SERVER_URL`，会先尝试发现现有 `plantuml-server` 容器，再按需要拉起临时容器
- `site-cli build` 会复用同一套 PlantUML server 机制
