from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .analyzer.github_client import GitHubClientError, fetch_repo_snapshot, parse_github_url
from .analyzer.mcp_config import extract_mcp_server_repos
from .analyzer.remote_validator import remote_response_code
from .analyzer.report import build_report
from .database import DatabaseError, get_report, list_top_checked_mcp_repositories, save_report
from .schemas import (
    AnalyzeConfigRequest,
    AnalyzeConfigResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ConfigAnalyzeResult,
    TopRepository,
)


app = FastAPI(title="MCPCheck API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("MCPCHECK_ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
MAX_CONFIG_ANALYSES = int(os.getenv("MCP_MAX_CONFIG_ANALYSES", "5"))
MAX_REMOTE_VALIDATIONS = int(os.getenv("MCP_MAX_REMOTE_VALIDATIONS", "5"))
MAX_CONFIG_SERVERS = int(os.getenv("MCP_MAX_CONFIG_SERVERS", "10"))
MAX_CONFIG_BYTES = int(os.getenv("MCP_MAX_CONFIG_BYTES", "50000"))


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/repositories/top", response_model=list[TopRepository])
def top_repositories() -> list[TopRepository]:
    try:
        return [TopRepository(**repo) for repo in list_top_checked_mcp_repositories(limit=10)]
    except DatabaseError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


@app.post("/api/analyze-config", response_model=AnalyzeConfigResponse)
def analyze_config(request: AnalyzeConfigRequest) -> AnalyzeConfigResponse:
    if len(request.config.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise HTTPException(status_code=413, detail=f"MCP config must be {MAX_CONFIG_BYTES} bytes or smaller.")
    try:
        servers = extract_mcp_server_repos(request.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    results: list[ConfigAnalyzeResult] = []
    if len(servers) > MAX_CONFIG_SERVERS:
        raise HTTPException(
            status_code=400,
            detail=f"Config includes {len(servers)} MCP servers. Analyze at most {MAX_CONFIG_SERVERS} at once.",
        )
    analyzable = [server for server in servers if server["repoUrl"]]
    if len(analyzable) > MAX_CONFIG_ANALYSES:
        raise HTTPException(
            status_code=400,
            detail=f"Config includes {len(analyzable)} GitHub-backed MCP servers. Analyze at most {MAX_CONFIG_ANALYSES} at once.",
        )
    remote_validations = [server for server in servers if server["healthCheckUrl"]]
    if len(remote_validations) > MAX_REMOTE_VALIDATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Config includes {len(remote_validations)} remote health URLs. Validate at most {MAX_REMOTE_VALIDATIONS} at once.",
        )

    for server in servers:
        server_name = server["serverName"]
        repo_url = server["repoUrl"]
        health_check_url = server["healthCheckUrl"]
        response_code, response_error = remote_response_code(health_check_url) if health_check_url else (None, None)
        if not repo_url and not health_check_url:
            results.append(
                ConfigAnalyzeResult(
                    serverName=server_name,
                    status="skipped",
                    error="No GitHub repository URL or remote health check URL found in this server config.",
                )
            )
            continue
        if not repo_url:
            results.append(
                ConfigAnalyzeResult(
                    serverName=server_name,
                    healthCheckUrl=health_check_url,
                    responseCode=response_code,
                    responseError=response_error,
                    status="validated",
                )
            )
            continue
        try:
            parse_github_url(repo_url)
            snapshot = fetch_repo_snapshot(repo_url)
            report = build_report(snapshot)
            report_id = save_report(report)
            results.append(
                ConfigAnalyzeResult(
                    serverName=server_name,
                    repoUrl=repo_url,
                    healthCheckUrl=health_check_url or None,
                    responseCode=response_code,
                    responseError=response_error,
                    reportId=report_id,
                    status="completed",
                    summary={
                        "overallScore": int(report["scores"]["overall"]),
                        "riskLevel": report["risk"]["level"],
                        "repoName": f"{report['repo']['owner']}/{report['repo']['name']}",
                    },
                )
            )
        except (ValueError, GitHubClientError, DatabaseError) as exc:
            results.append(
                ConfigAnalyzeResult(
                    serverName=server_name,
                    repoUrl=repo_url,
                    healthCheckUrl=health_check_url or None,
                    responseCode=response_code,
                    responseError=response_error,
                    status="failed",
                    error=str(exc),
                )
            )
    return AnalyzeConfigResponse(results=results)


@app.get("/api/reports/{report_id}")
def report(report_id: str) -> dict[str, object]:
    try:
        stored = get_report(report_id)
    except DatabaseError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not stored:
        raise HTTPException(status_code=404, detail="Report not found.")
    return stored
