from app.database import get_report, list_top_checked_mcp_repositories, save_report


def test_sqlite_fallback_saves_and_loads_report(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MCPCHECK_SQLITE_PATH", str(tmp_path / "reports.db"))
    report = {
        "id": "",
        "repo": {"url": "https://github.com/a/b", "owner": "a", "name": "b"},
        "scores": {"overall": 75},
        "risk": {"level": "Medium"},
    }

    report_id = save_report(report)
    loaded = get_report(report_id)

    assert loaded is not None
    assert loaded["id"] == report_id
    assert loaded["repo"]["owner"] == "a"


def test_top_checked_mcp_repositories_groups_and_filters(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("MCPCHECK_SQLITE_PATH", str(tmp_path / "reports.db"))

    def report(owner: str, name: str, confidence: float, is_likely: bool = True) -> dict:
        return {
            "id": "",
            "repo": {"url": f"https://github.com/{owner}/{name}", "owner": owner, "name": name},
            "mcpDetection": {"confidence": confidence, "isLikelyMcpServer": is_likely},
            "scores": {"overall": 75},
            "risk": {"level": "Medium"},
        }

    save_report(report("a", "mcp-one", 0.91))
    save_report(report("a", "mcp-one", 0.91))
    save_report(report("b", "mcp-two", 0.72))
    save_report(report("c", "not-mcp", 0.15, is_likely=False))

    top_repositories = list_top_checked_mcp_repositories()

    assert [repo["repoName"] for repo in top_repositories] == ["a/mcp-one", "b/mcp-two"]
    assert top_repositories[0]["checkCount"] == 2
    assert top_repositories[0]["confidence"] == 0.91
