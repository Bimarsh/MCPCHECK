from __future__ import annotations

import re
from dataclasses import dataclass

from .risk import classify_tool_name


TS_TOOL_PATTERNS = (
    re.compile(r"\b(?:server|mcp)\.tool\(\s*['\"]([A-Za-z0-9_.:-]+)['\"]", re.MULTILINE),
    re.compile(r"\bname\s*:\s*['\"]([A-Za-z0-9_.:-]+)['\"]", re.MULTILINE),
)
PY_DECORATOR_PATTERN = re.compile(
    r"@(mcp|server)\.tool\([^)]*\)\s*(?:\n\s*@[\w.()=,'\"\s-]+)*\n\s*def\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
PY_NAME_PATTERN = re.compile(r"\bname\s*=\s*['\"]([A-Za-z0-9_.:-]+)['\"]")


@dataclass(frozen=True)
class DetectedTool:
    name: str
    description: str
    hasInputSchema: bool
    riskLevel: str


def _nearby_window(content: str, position: int, size: int = 700) -> str:
    return content[max(position - 150, 0) : min(position + size, len(content))]


def _description_from(window: str) -> str:
    patterns = (
        r"description\s*:\s*['\"]([^'\"]{8,220})['\"]",
        r"description\s*=\s*['\"]([^'\"]{8,220})['\"]",
        r"['\"]([^'\"]{12,180})['\"]\s*,\s*(?:\{|z\.)",
    )
    for pattern in patterns:
        match = re.search(pattern, window, re.IGNORECASE | re.DOTALL)
        if match:
            return " ".join(match.group(1).split())
    return ""


def _has_schema(window: str) -> bool:
    lowered = window.lower()
    return any(token in lowered for token in ("inputschema", "input_schema", "z.object", "pydantic", "properties", "jsonschema"))


def extract_tools(files: list[object]) -> list[dict[str, object]]:
    seen: set[str] = set()
    tools: list[DetectedTool] = []
    for repo_file in files:
        path = getattr(repo_file, "path")
        content = getattr(repo_file, "content")
        lower_path = str(path).lower()
        matches: list[tuple[str, int]] = []
        if lower_path.endswith((".ts", ".tsx", ".js", ".jsx", ".json")):
            for pattern in TS_TOOL_PATTERNS:
                matches.extend((match.group(1), match.start()) for match in pattern.finditer(content))
        if lower_path.endswith(".py"):
            matches.extend((match.group(2), match.start()) for match in PY_DECORATOR_PATTERN.finditer(content))
            matches.extend((match.group(1), match.start()) for match in PY_NAME_PATTERN.finditer(content))
        for name, position in matches:
            if name in seen or len(name) > 80:
                continue
            seen.add(name)
            window = _nearby_window(content, position)
            tools.append(
                DetectedTool(
                    name=name,
                    description=_description_from(window),
                    hasInputSchema=_has_schema(window),
                    riskLevel=classify_tool_name(name),
                )
            )
    return [tool.__dict__ for tool in tools]

