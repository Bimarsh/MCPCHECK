from __future__ import annotations

from .tool_extractor import extract_tools


MCP_PATTERNS = (
    ("README mentions Model Context Protocol", "model context protocol"),
    ("README mentions MCP server", "mcp server"),
    ("package.json references @modelcontextprotocol/sdk", "@modelcontextprotocol/sdk"),
    ("Python dependencies reference MCP packages", "mcp"),
    ("Source contains server.tool definitions", "server.tool"),
    ("Source contains mcp.tool definitions", "mcp.tool"),
    ("Source contains listTools", "listtools"),
    ("Source contains CallToolRequest", "calltoolrequest"),
    ("Source imports MCP Server", "server from @modelcontextprotocol/sdk"),
    ("Source references FastMCP", "fastmcp"),
    ("Source references resources/list", "resources/list"),
    ("Source references prompts/list", "prompts/list"),
    ("Source references tools/list", "tools/list"),
)


def detect_mcp(files: list[object]) -> dict[str, object]:
    evidence: list[str] = []
    combined = "\n".join(getattr(repo_file, "content") for repo_file in files).lower()
    by_path = {str(getattr(repo_file, "path")).lower(): getattr(repo_file, "content").lower() for repo_file in files}
    for label, pattern in MCP_PATTERNS:
        if pattern == "mcp":
            dependency_text = "\n".join(by_path.get(path, "") for path in ("requirements.txt", "pyproject.toml"))
            if "mcp" in dependency_text or "modelcontextprotocol" in dependency_text:
                evidence.append(label)
            continue
        if pattern in combined:
            evidence.append(label)
    tools = extract_tools(files)
    if tools and "Detected MCP-style tool definitions" not in evidence:
        evidence.append("Detected MCP-style tool definitions")
    confidence = min(0.98, round(0.2 + (len(evidence) * 0.14), 2)) if evidence else 0.05
    return {
        "isLikelyMcpServer": bool(evidence),
        "confidence": confidence,
        "evidence": evidence,
        "detectedCapabilities": {"tools": tools, "resources": [], "prompts": []},
    }

