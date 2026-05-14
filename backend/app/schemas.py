from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["Low", "Medium", "High"]
Severity = Literal["info", "warning", "critical"]


class AnalyzeRequest(BaseModel):
    repoUrl: str = Field(min_length=1)


class AnalyzeConfigRequest(BaseModel):
    config: str = Field(min_length=1)


class AnalyzeSummary(BaseModel):
    overallScore: int
    riskLevel: RiskLevel
    repoName: str


class AnalyzeResponse(BaseModel):
    reportId: str
    status: Literal["completed"]
    summary: AnalyzeSummary


class ConfigAnalyzeResult(BaseModel):
    serverName: str
    repoUrl: str | None = None
    healthCheckUrl: str | None = None
    responseCode: int | None = None
    responseError: str | None = None
    reportId: str | None = None
    status: Literal["completed", "validated", "failed", "skipped"]
    summary: AnalyzeSummary | None = None
    error: str | None = None


class AnalyzeConfigResponse(BaseModel):
    results: list[ConfigAnalyzeResult]


class TopRepository(BaseModel):
    repoUrl: str
    repoName: str
    checkCount: int
    confidence: float
    overallScore: int
    riskLevel: RiskLevel
    latestReportId: str


class ReportRecord(BaseModel):
    id: str
    repo_url: str
    repo_owner: str
    repo_name: str
    overall_score: int
    risk_level: RiskLevel
    raw_json: dict[str, Any]
