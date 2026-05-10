import pytest

from app.analyzer.github_client import parse_github_url, select_relevant_files


def test_parse_github_url_accepts_repo_url():
    parsed = parse_github_url("https://github.com/modelcontextprotocol/servers")

    assert parsed.owner == "modelcontextprotocol"
    assert parsed.name == "servers"
    assert parsed.full_name == "modelcontextprotocol/servers"


def test_parse_github_url_rejects_non_github():
    with pytest.raises(ValueError):
        parse_github_url("https://example.com/org/repo")


def test_select_relevant_files_enforces_limits():
    tree = [
        {"type": "blob", "path": "README.md", "size": 100},
        {"type": "blob", "path": "src/server.ts", "size": 100},
        {"type": "blob", "path": "large.bin", "size": 1},
        {"type": "blob", "path": "tests/test_server.py", "size": 999999},
    ]

    selected, skipped = select_relevant_files(tree, max_files=5, max_bytes=200)

    assert [item["path"] for item in selected] == ["README.md", "src/server.ts"]
    assert skipped == ["tests/test_server.py: skipped because it is larger than 200 bytes"]

