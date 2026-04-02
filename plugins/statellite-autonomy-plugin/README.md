# Satellite Autonomy Plugin Bundle

This directory is the clean Codex plugin bundle for the repository.

- `skills/` is a symlink to the repo root skill inventory.
- `.codex-plugin/plugin.json` contains the plugin metadata consumed by Codex.

This bundle is intentionally `skills`-only. Repository MCP servers stay outside the plugin
startup path and are invoked manually from the repo when needed.

Install or cache this bundle, not the full repo root, when registering the plugin with Codex.
