from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .risk import contains_file_mutation, contains_shell_usage


def _content(files: list[object], path: str) -> str:
    for repo_file in files:
        if str(getattr(repo_file, "path")).lower() == path:
            return str(getattr(repo_file, "content"))
    return ""


def _has_file(files: list[object], names: set[str]) -> bool:
    return any(str(getattr(repo_file, "path")).lower() in names for repo_file in files)


def _has_prefix(files: list[object], prefix: str) -> bool:
    return any(str(getattr(repo_file, "path")).lower().startswith(prefix) for repo_file in files)


def _readme_has(readme: str, words: tuple[str, ...]) -> bool:
    lowered = readme.lower()
    return any(word in lowered for word in words)


def score_report(repo: dict[str, Any], files: list[object], detection: dict[str, Any]) -> tuple[dict[str, int], dict[str, Any], list[dict[str, str]], list[str]]:
    readme = _content(files, "readme.md")
    all_contents = [str(getattr(file, "content")) for file in files]
    tools = detection["detectedCapabilities"]["tools"]
    documentation = 0
    documentation += 5 if readme else 0
    documentation += 5 if _readme_has(readme, ("mcp", "model context protocol", "server", "tool")) else 0
    documentation += 4 if _readme_has(readme, ("install", "setup", "usage", "run")) else 0
    documentation += 3 if _readme_has(readme, ("env", "environment", "api key", "token", "auth", "permission", "scope")) else 0
    documentation += 3 if _readme_has(readme, ("example", "prompt", "claude", "cursor")) else 0
    installability = 0
    installability += 5 if _has_file(files, {"package.json", "pyproject.toml", "requirements.txt"}) else 0
    installability += 4 if _readme_has(readme, ("npm", "npx", "python", "uv", "pip", "node", "docker run")) else 0
    installability += 3 if _has_file(files, {"dockerfile", "docker-compose.yml"}) else 0
    installability += 3 if _readme_has(readme, ("mcpservers", "claude_desktop_config", "cursor")) else 0
    described_tools = [tool for tool in tools if tool.get("description")]
    schema_tools = [tool for tool in tools if tool.get("hasInputSchema")]
    schema_quality = 0
    schema_quality += 5 if detection["isLikelyMcpServer"] and detection["confidence"] >= 0.5 else 0
    schema_quality += 5 if tools else 0
    schema_quality += 5 if tools and len(described_tools) == len(tools) else 0
    schema_quality += 5 if tools and len(schema_tools) == len(tools) else 0
    permission_docs = _readme_has(readme, ("permission", "scope", "read-only", "auth", "token"))
    env_docs = _readme_has(readme, ("env", "environment", "api key", "token"))
    has_high = any(tool.get("riskLevel") == "High" for tool in tools)
    has_medium = any(tool.get("riskLevel") == "Medium" for tool in tools)
    shell_usage = contains_shell_usage(all_contents)
    file_mutation = contains_file_mutation(all_contents)
    security = 20
    deductions: list[str] = []
    if has_high:
        security -= 5
        deductions.append("High-risk tool keywords detected")
    if has_medium:
        security -= 3
        deductions.append("Medium-risk tool keywords detected")
    if not permission_docs:
        security -= 4
        deductions.append("No explicit permission or scope documentation")
    if not env_docs:
        security -= 3
        deductions.append("Environment variables are not documented")
    if shell_usage:
        security -= 3
        deductions.append("Shell or subprocess usage detected")
    if file_mutation:
        security -= 2
        deductions.append("File write or delete patterns detected")
    security = max(0, security)
    maintenance = 0
    if repo.get("lastCommitDate"):
        try:
            last_commit = datetime.fromisoformat(str(repo["lastCommitDate"]).replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - last_commit).days
            maintenance += 5 if age_days <= 90 else 0
        except ValueError:
            pass
    maintenance += 4 if repo.get("license") else 0
    maintenance += 3 if int(repo.get("stars") or 0) > 5 else 0
    maintenance += 3
    tests_examples = 0
    tests_examples += 5 if _has_prefix(files, "tests/") or any("test" in str(getattr(file, "path")).lower() for file in files) else 0
    tests_examples += 5 if _has_prefix(files, "examples/") or _readme_has(readme, ("example", "sample config")) else 0
    scores = {
        "documentation": documentation,
        "installability": installability,
        "schemaQuality": schema_quality,
        "security": security,
        "maintenance": maintenance,
        "testsExamples": tests_examples,
    }
    scores["overall"] = sum(scores.values())
    if security < 8 or (has_high and not permission_docs):
        risk_level = "High"
    elif 8 <= security <= 14:
        risk_level = "Medium"
    else:
        risk_level = "Low"
    risk = {"level": risk_level, "reasons": deductions}
    findings: list[dict[str, str]] = []
    fixes: list[str] = []
    if not detection["isLikelyMcpServer"]:
        findings.append({"severity": "warning", "category": "MCP Detection", "title": "No MCP evidence found", "description": "This repository does not look like an MCP server from static signals.", "recommendation": "Add clear README and dependency references if this is an MCP server."})
    if not permission_docs:
        findings.append({"severity": "warning", "category": "Security", "title": "Permission documentation missing", "description": "The README does not clearly document permissions, scopes, or authentication requirements.", "recommendation": "Add a permissions and scopes section to the README."})
        fixes.append("Add a permissions section to README.")
    if tools and len(described_tools) < len(tools):
        findings.append({"severity": "warning", "category": "MCP Schema Quality", "title": "Tool descriptions are incomplete", "description": "One or more detected tools do not have a nearby static description.", "recommendation": "Add concise descriptions for each tool."})
        fixes.append("Add descriptions for each MCP tool.")
    if tools and len(schema_tools) < len(tools):
        fixes.append("Add explicit input schemas for all tools.")
    if not env_docs:
        fixes.append("Document environment variables.")
    if not _readme_has(readme, ("mcpservers", "claude", "cursor")):
        fixes.append("Add a minimal Claude Desktop or Cursor config example.")
    if shell_usage:
        findings.append({"severity": "critical", "category": "Security", "title": "Shell execution pattern detected", "description": "Static analysis found shell or subprocess usage.", "recommendation": "Document safeguards and avoid exposing shell execution through MCP tools."})
    return scores, risk, findings, list(dict.fromkeys(fixes))

