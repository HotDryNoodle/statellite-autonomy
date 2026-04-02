#!/usr/bin/env bash
set -euo pipefail

PLUGIN_NAME="statellite-autonomy-plugin"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_SOURCE="${REPO_ROOT}/plugins/${PLUGIN_NAME}"
PLUGIN_HOME="${HOME}/plugins/${PLUGIN_NAME}"
CODEX_CACHE_ROOT="${HOME}/.codex/plugins/cache/local-plugins/${PLUGIN_NAME}"
CACHE_BUNDLE_ID="workspace"
CODEX_CACHE_PLUGIN="${CODEX_CACHE_ROOT}/${CACHE_BUNDLE_ID}"
MARKETPLACE_PATH="${HOME}/.agents/plugins/marketplace.json"

mkdir -p "${HOME}/plugins" "${HOME}/.agents/plugins"

if [[ -e "${PLUGIN_HOME}" && ! -L "${PLUGIN_HOME}" ]]; then
  echo "Refusing to overwrite existing non-symlink path: ${PLUGIN_HOME}" >&2
  exit 1
fi

ln -sfn "${PLUGIN_SOURCE}" "${PLUGIN_HOME}"
mkdir -p "${HOME}/.codex/plugins/cache/local-plugins"
rm -rf "${CODEX_CACHE_ROOT}"
mkdir -p "${CODEX_CACHE_ROOT}"
cp -aL "${PLUGIN_SOURCE}" "${CODEX_CACHE_PLUGIN}"
find "${CODEX_CACHE_PLUGIN}" -name '.mcp.json' -delete

python3 - "${MARKETPLACE_PATH}" <<'PY'
import json
import sys
from pathlib import Path

marketplace_path = Path(sys.argv[1])
entry = {
    "name": "statellite-autonomy-plugin",
    "source": {
        "source": "local",
        "path": "./plugins/statellite-autonomy-plugin"
    },
    "policy": {
        "installation": "INSTALLED_BY_DEFAULT",
        "authentication": "ON_INSTALL"
    },
    "category": "Coding"
}

if marketplace_path.exists():
    data = json.loads(marketplace_path.read_text(encoding="utf-8"))
else:
    data = {
        "name": "local-plugins",
        "interface": {"displayName": "Local Plugins"},
        "plugins": []
    }

plugins = [plugin for plugin in data.get("plugins", []) if plugin.get("name") != entry["name"]]
plugins.append(entry)
data["plugins"] = plugins

marketplace_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

echo "Installed local plugin symlink at ${PLUGIN_HOME}"
echo "Installed Codex cache copy at ${CODEX_CACHE_PLUGIN}"
echo "Removed plugin-bundled .mcp.json files from the Codex cache copy"
echo "Wrote marketplace entry to ${MARKETPLACE_PATH}"
echo "Restart Codex to pick up the plugin."
