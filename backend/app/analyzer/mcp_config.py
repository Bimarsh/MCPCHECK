from __future__ import annotations

import json
import re
from typing import Any


GITHUB_URL_RE = re.compile(
    r"(?:git\+)?https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?]\S*)?$"
)
GITHUB_SHORTHAND_RE = re.compile(r"^github:([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$")
GITHUB_HOST_RE = re.compile(r"^github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?]\S*)?$")
HTTP_URL_RE = re.compile(r"^https?://[^\s\"']+$")
HEALTH_URL_KEYS = {"health", "healthcheck", "healthcheckurl", "healthurl", "url", "endpoint"}


def _strings_from(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_strings_from(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_strings_from(item))
        return strings
    return []


def _github_url_from_text(value: str) -> str | None:
    cleaned = value.strip().strip("'\"")
    for pattern in (GITHUB_URL_RE, GITHUB_SHORTHAND_RE, GITHUB_HOST_RE):
        match = pattern.search(cleaned)
        if match:
            owner, repo = match.groups()
            return f"https://github.com/{owner}/{repo}"
    return None


def _health_url_from_config(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    for key, item in value.items():
        normalized_key = str(key).replace("_", "").replace("-", "").lower()
        if normalized_key not in HEALTH_URL_KEYS or not isinstance(item, str):
            continue
        cleaned = item.strip()
        if HTTP_URL_RE.match(cleaned) and "github.com/" not in cleaned.lower():
            return cleaned
    return None


def extract_mcp_server_repos(config_text: str) -> list[dict[str, str]]:
    try:
        config = json.loads(config_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Paste a valid JSON MCP config.") from exc
    if not isinstance(config, dict):
        raise ValueError("MCP config must be a JSON object.")
    servers = config.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        raise ValueError("MCP config must include an mcpServers object.")

    extracted: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for server_name, server_config in servers.items():
        repo_url = None
        health_check_url = _health_url_from_config(server_config)
        for value in _strings_from(server_config):
            repo_url = _github_url_from_text(value)
            if repo_url:
                break
        key = (str(server_name), repo_url or "", health_check_url or "")
        if key in seen:
            continue
        seen.add(key)
        extracted.append({"serverName": str(server_name), "repoUrl": repo_url or "", "healthCheckUrl": health_check_url or ""})
    return extracted
