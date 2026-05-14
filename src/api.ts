import type { AnalyzeConfigResponse, AnalyzeResponse, Report, TopRepository } from "./types";

async function readJson<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : "Request failed.";
    throw new Error(detail);
  }
  return payload as T;
}

export async function analyzeRepo(repoUrl: string): Promise<AnalyzeResponse> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repoUrl })
  });
  return readJson<AnalyzeResponse>(response);
}

export async function analyzeMcpConfig(config: string): Promise<AnalyzeConfigResponse> {
  const response = await fetch("/api/analyze-config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ config })
  });
  return readJson<AnalyzeConfigResponse>(response);
}

export async function fetchReport(reportId: string): Promise<Report> {
  const response = await fetch(`/api/reports/${encodeURIComponent(reportId)}`);
  return readJson<Report>(response);
}

export async function fetchTopRepositories(): Promise<TopRepository[]> {
  const response = await fetch("/api/repositories/top");
  return readJson<TopRepository[]>(response);
}
