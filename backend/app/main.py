from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .analyzer.github_client import GitHubClientError, fetch_repo_snapshot, parse_github_url
from .analyzer.report import build_report
from .database import DatabaseError, get_report, save_report
from .schemas import AnalyzeRequest, AnalyzeResponse


app = FastAPI(title="MCPCheck API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    try:
        parse_github_url(request.repoUrl)
        snapshot = fetch_repo_snapshot(request.repoUrl)
        report = build_report(snapshot)
        report_id = save_report(report)
        return AnalyzeResponse(
            reportId=report_id,
            status="completed",
            summary={
                "overallScore": int(report["scores"]["overall"]),
                "riskLevel": report["risk"]["level"],
                "repoName": f"{report['repo']['owner']}/{report['repo']['name']}",
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GitHubClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/reports/{report_id}")
def report(report_id: str) -> dict[str, object]:
    try:
        stored = get_report(report_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not stored:
        raise HTTPException(status_code=404, detail="Report not found.")
    return stored

