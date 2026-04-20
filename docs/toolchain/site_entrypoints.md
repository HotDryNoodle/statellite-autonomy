# Site Entrypoints

- `uv run --group site --no-default-groups site-cli build`
- `uv run --group site --no-default-groups site-cli serve`
- `uv run --group site --no-default-groups site-cli open`
- `uv run --group site --no-default-groups site-cli start`
- `uv run --group site --no-default-groups site-cli stop`

输出路径：

- Staging：`site/_staging/`
- 静态站点：`site/_generated/`

说明：

- `site-cli` 负责把 `README.md`、`contracts/`、`architecture/blueprints/`、`docs/toolchain/` 等资产编排成只读站点
- 站点自身不修改权威源文件
