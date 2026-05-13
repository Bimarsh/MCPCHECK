from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL,
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    overall_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    raw_json TEXT NOT NULL
);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL,
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    overall_score INTEGER NOT NULL,
    risk_level TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_json JSONB NOT NULL
);
"""


class DatabaseError(RuntimeError):
    pass


def _database_url() -> str:
    return os.getenv("DATABASE_URL") or f"sqlite:///{os.getenv('MCPCHECK_SQLITE_PATH', '/tmp/mcpcheck.db')}"


def using_postgres() -> bool:
    return _database_url().startswith(("postgres://", "postgresql://"))


@contextmanager
def _sqlite_conn(path: str) -> Iterator[sqlite3.Connection]:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def _postgres_conn() -> Iterator[Any]:
    try:
        import psycopg
    except ImportError as exc:
        raise DatabaseError("psycopg is required for Neon/Postgres DATABASE_URL.") from exc
    with psycopg.connect(_database_url()) as conn:
        yield conn


def init_db() -> None:
    if using_postgres():
        with _postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_POSTGRES)
            conn.commit()
        return
    path = _database_url().replace("sqlite:///", "", 1)
    with _sqlite_conn(path) as conn:
        conn.execute(SCHEMA_SQLITE)


def save_report(report: dict[str, Any]) -> str:
    init_db()
    report_id = report.get("id") or str(uuid.uuid4())
    report["id"] = report_id
    repo = report["repo"]
    scores = report["scores"]
    risk = report["risk"]
    if using_postgres():
        from psycopg.types.json import Json

        with _postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO reports (id, repo_url, repo_owner, repo_name, overall_score, risk_level, raw_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report_id,
                        repo["url"],
                        repo["owner"],
                        repo["name"],
                        int(scores["overall"]),
                        risk["level"],
                        Json(report),
                    ),
                )
            conn.commit()
        return report_id
    path = _database_url().replace("sqlite:///", "", 1)
    with _sqlite_conn(path) as conn:
        conn.execute(
            """
            INSERT INTO reports (id, repo_url, repo_owner, repo_name, overall_score, risk_level, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                repo["url"],
                repo["owner"],
                repo["name"],
                int(scores["overall"]),
                risk["level"],
                json.dumps(report),
            ),
        )
    return report_id


def get_report(report_id: str) -> dict[str, Any] | None:
    init_db()
    if using_postgres():
        with _postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT raw_json FROM reports WHERE id = %s", (report_id,))
                row = cur.fetchone()
                if not row:
                    return None
                raw = row[0]
                return raw if isinstance(raw, dict) else json.loads(raw)
    path = _database_url().replace("sqlite:///", "", 1)
    with _sqlite_conn(path) as conn:
        row = conn.execute("SELECT raw_json FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            return None
        return json.loads(row["raw_json"])


def _decode_report(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else json.loads(raw)


def list_top_checked_mcp_repositories(limit: int = 10) -> list[dict[str, Any]]:
    init_db()
    rows: list[Any]
    if using_postgres():
        with _postgres_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT raw_json
                    FROM reports
                    ORDER BY created_at DESC
                    """
                )
                rows = cur.fetchall()
    else:
        path = _database_url().replace("sqlite:///", "", 1)
        with _sqlite_conn(path) as conn:
            rows = conn.execute(
                """
                SELECT raw_json
                FROM reports
                ORDER BY created_at DESC
                """
            ).fetchall()

    repos: dict[str, dict[str, Any]] = {}
    for row in rows:
        raw = row[0] if isinstance(row, tuple) else row["raw_json"]
        report = _decode_report(raw)
        repo = report.get("repo") or {}
        owner = str(repo.get("owner") or "").strip()
        name = str(repo.get("name") or "").strip()
        if not owner or not name:
            continue
        key = f"{owner.lower()}/{name.lower()}"
        entry = repos.setdefault(
            key,
            {
                "repoUrl": repo.get("url") or f"https://github.com/{owner}/{name}",
                "repoName": f"{owner}/{name}",
                "checkCount": 0,
                "confidence": float((report.get("mcpDetection") or {}).get("confidence") or 0),
                "overallScore": int((report.get("scores") or {}).get("overall") or 0),
                "riskLevel": (report.get("risk") or {}).get("level") or "Medium",
                "latestReportId": report.get("id") or "",
                "isLikelyMcpServer": bool((report.get("mcpDetection") or {}).get("isLikelyMcpServer")),
            },
        )
        entry["checkCount"] += 1

    top_repos = [repo for repo in repos.values() if repo.pop("isLikelyMcpServer")]
    return sorted(top_repos, key=lambda repo: (-repo["checkCount"], -repo["confidence"], repo["repoName"]))[:limit]
