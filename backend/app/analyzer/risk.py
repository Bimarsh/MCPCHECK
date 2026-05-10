from __future__ import annotations

import re


HIGH_RISK_KEYWORDS = {
    "exec",
    "execute",
    "shell",
    "command",
    "terminal",
    "delete",
    "remove",
    "write_file",
    "filesystem",
    "upload",
    "deploy",
    "payment",
    "transfer",
    "send_email",
    "send_message",
    "create_user",
    "update_user",
    "database_write",
    "sql_query",
    "run_query",
}
MEDIUM_RISK_KEYWORDS = {"create", "update", "edit", "post", "publish", "comment", "merge", "approve", "mutate", "insert"}
LOW_RISK_KEYWORDS = {"search", "list", "get", "read", "fetch", "describe"}
SHELL_PATTERNS = (r"\bsubprocess\.", r"\bos\.system\(", r"\bchild_process\b", r"\bexecSync\(", r"\bspawn\(")
FILE_WRITE_PATTERNS = (r"\bwriteFile", r"\bunlink\(", r"\brm\s+-", r"\.write_text\(", r"\bopen\([^)]*,\s*['\"]w")


def classify_tool_name(name: str) -> str:
    normalized = name.lower().replace("-", "_")
    if any(keyword in normalized for keyword in HIGH_RISK_KEYWORDS):
        return "High"
    if any(re.search(rf"(^|_){re.escape(keyword)}($|_)", normalized) for keyword in MEDIUM_RISK_KEYWORDS):
        return "Medium"
    if any(re.search(rf"(^|_){re.escape(keyword)}($|_)", normalized) for keyword in LOW_RISK_KEYWORDS):
        return "Low"
    return "Medium"


def contains_shell_usage(contents: list[str]) -> bool:
    joined = "\n".join(contents)
    return any(re.search(pattern, joined) for pattern in SHELL_PATTERNS)


def contains_file_mutation(contents: list[str]) -> bool:
    joined = "\n".join(contents)
    return any(re.search(pattern, joined) for pattern in FILE_WRITE_PATTERNS)

