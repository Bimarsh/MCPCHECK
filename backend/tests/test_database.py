from app.database import get_report, save_report


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

