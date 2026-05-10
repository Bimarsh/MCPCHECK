from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any


GITHUB_RE = re.compile(r"^https?://github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?(?:[?#].*)?$")
RELEVANT_ROOT_FILES = {
    "readme.md",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "dockerfile",
    "docker-compose.yml",
}
RELEVANT_PREFIXES = ("src/", "server/", "examples/", "tests/")
RELEVANT_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".toml", ".md", ".yml", ".yaml")
DEFAULT_MAX_FILES = int(os.getenv("MCP_MAX_FILES", "80"))
DEFAULT_MAX_BYTES = int(os.getenv("MCP_MAX_FILE_BYTES", "120000"))
DEFAULT_MAX_TREE_ITEMS = int(os.getenv("MCP_MAX_TREE_ITEMS", "2500"))


class GitHubClientError(RuntimeError):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ParsedRepo:
    owner: str
    name: str
    url: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class RepoFile:
    path: str
    content: str
    size: int


@dataclass(frozen=True)
class RepoSnapshot:
    parsed: ParsedRepo
    metadata: dict[str, Any]
    files: list[RepoFile]
    skipped: list[str]


def parse_github_url(url: str) -> ParsedRepo:
    match = GITHUB_RE.match(url.strip())
    if not match:
        raise ValueError("Enter a valid GitHub repository URL like https://github.com/org/repo.")
    owner, name = match.groups()
    if owner in {"-", "."} or name in {"-", "."}:
        raise ValueError("GitHub owner and repository name are required.")
    return ParsedRepo(owner=owner, name=name, url=f"https://github.com/{owner}/{name}")


def _github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "mcpcheck-static-analyzer",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_json(url: str) -> Any:
    request = urllib.request.Request(url, headers=_github_headers())
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GitHubClientError("GitHub repository not found.", 404) from exc
        if exc.code in {403, 429}:
            raise GitHubClientError("GitHub API rate limit reached. Configure GITHUB_TOKEN and try again.", 429) from exc
        raise GitHubClientError(f"GitHub API error: HTTP {exc.code}.", 502) from exc
    except urllib.error.URLError as exc:
        raise GitHubClientError("Could not reach GitHub. Check network connectivity and try again.", 502) from exc


def _fetch_text_file(download_url: str, max_bytes: int) -> str:
    request = urllib.request.Request(download_url, headers=_github_headers())
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise GitHubClientError("File exceeds configured size limit.", 413)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GitHubClientError("File is not valid UTF-8 text.", 415) from exc


def _is_relevant(path: str) -> bool:
    normalized = path.lower()
    basename = normalized.rsplit("/", 1)[-1]
    if basename in RELEVANT_ROOT_FILES and "/" not in normalized:
        return True
    if normalized.startswith(RELEVANT_PREFIXES) and normalized.endswith(RELEVANT_EXTENSIONS):
        return True
    return False


def select_relevant_files(tree: list[dict[str, Any]], max_files: int, max_bytes: int) -> tuple[list[dict[str, Any]], list[str]]:
    selected: list[dict[str, Any]] = []
    skipped: list[str] = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = str(item.get("path", ""))
        size = int(item.get("size") or 0)
        if not _is_relevant(path):
            continue
        if size > max_bytes:
            skipped.append(f"{path}: skipped because it is larger than {max_bytes} bytes")
            continue
        selected.append(item)
        if len(selected) >= max_files:
            skipped.append(f"file limit reached at {max_files} files")
            break
    return selected, skipped


def fetch_repo_snapshot(
    repo_url: str,
    max_files: int = DEFAULT_MAX_FILES,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_tree_items: int = DEFAULT_MAX_TREE_ITEMS,
) -> RepoSnapshot:
    parsed = parse_github_url(repo_url)
    api_base = f"https://api.github.com/repos/{parsed.owner}/{parsed.name}"
    repo = _get_json(api_base)
    branch = repo.get("default_branch") or "main"
    commits = _get_json(f"{api_base}/commits/{urllib.parse.quote(branch, safe='')}")
    tree_data = _get_json(f"{api_base}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1")
    tree = tree_data.get("tree") or []
    skipped: list[str] = []
    if len(tree) > max_tree_items:
        skipped.append(f"repo tree has {len(tree)} items; only first {max_tree_items} were considered")
        tree = tree[:max_tree_items]
    selected, selected_skipped = select_relevant_files(tree, max_files=max_files, max_bytes=max_bytes)
    skipped.extend(selected_skipped)
    files: list[RepoFile] = []
    for item in selected:
        path = str(item["path"])
        raw_url = f"https://raw.githubusercontent.com/{parsed.owner}/{parsed.name}/{branch}/{path}"
        try:
            content = _fetch_text_file(raw_url, max_bytes=max_bytes)
            files.append(RepoFile(path=path, content=content, size=len(content.encode("utf-8"))))
        except GitHubClientError as exc:
            skipped.append(f"{path}: {exc}")
    license_info = repo.get("license") or {}
    commit_date = (((commits.get("commit") or {}).get("committer") or {}).get("date"))
    metadata = {
        "url": parsed.url,
        "owner": parsed.owner,
        "name": parsed.name,
        "description": repo.get("description") or "",
        "stars": repo.get("stargazers_count") or 0,
        "forks": repo.get("forks_count") or 0,
        "defaultBranch": branch,
        "lastCommitDate": commit_date,
        "license": license_info.get("spdx_id") or license_info.get("name") or "",
        "detectedLanguages": [],
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
    }
    return RepoSnapshot(parsed=parsed, metadata=metadata, files=files, skipped=skipped)

