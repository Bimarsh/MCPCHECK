from __future__ import annotations

import json
from typing import Any


def generate_client_configs(repo: dict[str, Any], files: list[object]) -> dict[str, str]:
    file_map = {str(getattr(file, "path")).lower(): getattr(file, "content") for file in files}
    server_name = repo["name"]
    env: dict[str, str] = {}
    readme = file_map.get("readme.md", "")
    for token in ("API_KEY", "TOKEN", "ACCESS_TOKEN", "GITHUB_TOKEN"):
        if token.lower() in readme.lower():
            env[token] = f"your_{token.lower()}_here"
    package_json = file_map.get("package.json")
    pyproject = file_map.get("pyproject.toml")
    requirements = file_map.get("requirements.txt")
    if package_json:
        config = {"mcpServers": {server_name: {"command": "npx", "args": ["-y", repo["url"]], "env": env}}}
    elif pyproject or requirements:
        module_name = server_name.replace("-", "_")
        config = {"mcpServers": {server_name: {"command": "python", "args": ["-m", module_name], "env": env}}}
    else:
        config = {"mcpServers": {server_name: {"command": "CHANGE_ME", "args": [], "env": env}}}
    return {
        "claudeDesktop": json.dumps(config, indent=2),
        "cursor": json.dumps(config, indent=2),
    }

