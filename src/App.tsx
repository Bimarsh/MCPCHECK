import { AlertTriangle, CheckCircle2, ExternalLink, GitBranch, Loader2, ShieldAlert, Trophy } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { analyzeMcpConfig, analyzeRepo, fetchReport, fetchTopRepositories } from "./api";
import type { ConfigAnalyzeResult, Report, RiskLevel, TopRepository } from "./types";

const examples = [
  "https://github.com/modelcontextprotocol/servers",
  "https://github.com/modelcontextprotocol/python-sdk"
];

function isGitHubUrl(value: string) {
  return /^https?:\/\/github\.com\/[^/\s]+\/[^/\s#?]+\/?/.test(value.trim());
}

function riskClass(level: RiskLevel) {
  return `badge badge-${level.toLowerCase()}`;
}

function responseCodeLabel(result: ConfigAnalyzeResult) {
  if (typeof result.responseCode === "number") {
    return String(result.responseCode);
  }
  return result.healthCheckUrl ? result.responseError || "Unavailable" : "Not available";
}

function HomePage() {
  const [repoUrl, setRepoUrl] = useState("");
  const [mcpConfig, setMcpConfig] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [configError, setConfigError] = useState("");
  const [isConfigLoading, setIsConfigLoading] = useState(false);
  const [configResults, setConfigResults] = useState<ConfigAnalyzeResult[]>([]);
  const [topRepositories, setTopRepositories] = useState<TopRepository[]>([]);
  const [topRepositoriesError, setTopRepositoriesError] = useState("");

  useEffect(() => {
    fetchTopRepositories()
      .then(setTopRepositories)
      .catch((err) => setTopRepositoriesError(err instanceof Error ? err.message : "Unable to load top repositories."));
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    if (!isGitHubUrl(repoUrl)) {
      setError("Enter a valid GitHub repository URL.");
      return;
    }
    setIsLoading(true);
    try {
      const result = await analyzeRepo(repoUrl.trim());
      window.history.pushState(null, "", `/reports/${result.reportId}`);
      window.dispatchEvent(new PopStateEvent("popstate"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function submitConfig(event: React.FormEvent) {
    event.preventDefault();
    setConfigError("");
    setConfigResults([]);
    if (!mcpConfig.trim()) {
      setConfigError("Paste an MCP config JSON object.");
      return;
    }
    setIsConfigLoading(true);
    try {
      const result = await analyzeMcpConfig(mcpConfig.trim());
      setConfigResults(result.results);
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : "Config analysis failed.");
    } finally {
      setIsConfigLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <div className="eyebrow"><ShieldAlert size={16} /> MCPCheck</div>
          <h1>Static quality and security reports for MCP servers</h1>
          <p className="hero-lede">Check MCP servers before your agents use them.</p>
          <p>
            Paste a public GitHub repository or MCP config and get deterministic reports without running untrusted server code.
          </p>
        </div>
        <div className="analyze-panel">
          <form onSubmit={submit}>
            <label htmlFor="repo-url">GitHub repository URL</label>
            <div className="input-row">
              <GitBranch size={20} />
              <input
                id="repo-url"
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                placeholder="https://github.com/org/repo"
              />
              <button type="submit" disabled={isLoading}>
                {isLoading ? <Loader2 className="spin" size={18} /> : <CheckCircle2 size={18} />}
                Analyze
              </button>
            </div>
            {error ? <p className="error">{error}</p> : null}
            <div className="examples">
              {examples.map((example) => (
                <button key={example} type="button" onClick={() => setRepoUrl(example)}>
                  {example.replace("https://github.com/", "")}
                </button>
              ))}
            </div>
          </form>

          <div className="config-divider"><span>or paste MCP config</span></div>

          <form className="config-form" onSubmit={submitConfig}>
            <label htmlFor="mcp-config">MCP config JSON</label>
            <textarea
              id="mcp-config"
              value={mcpConfig}
              onChange={(event) => setMcpConfig(event.target.value)}
              placeholder={'{\n  "mcpServers": {\n    "server-name": {\n      "command": "npx",\n      "args": ["-y", "https://github.com/org/repo"],\n      "healthCheckUrl": "https://example.com/health"\n    }\n  }\n}'}
            />
            <button type="submit" disabled={isConfigLoading}>
              {isConfigLoading ? <Loader2 className="spin" size={18} /> : <CheckCircle2 size={18} />}
              Analyze config
            </button>
          </form>
          {configError ? <p className="error">{configError}</p> : null}
          {configResults.length ? (
            <div className="config-results">
              {configResults.map((result) => (
                <div className="config-result" key={`${result.serverName}-${result.repoUrl || "missing"}`}>
                  <strong>{result.serverName}</strong>
                  {result.status === "completed" && result.reportId && result.summary ? (
                    <>
                      <a href={`/reports/${encodeURIComponent(result.reportId)}`}>{result.summary.repoName}</a>
                      <span>Response {responseCodeLabel(result)}</span>
                      <span>{result.summary.overallScore}/100</span>
                      <span>{result.summary.riskLevel} risk</span>
                    </>
                  ) : result.status === "validated" ? (
                    <>
                      <span>{result.healthCheckUrl || "Remote URL"}</span>
                      <span>Response {responseCodeLabel(result)}</span>
                    </>
                  ) : (
                    <>
                      <span>{result.error || "Analysis did not complete."}</span>
                      <span>Response {responseCodeLabel(result)}</span>
                    </>
                  )}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </section>

      <section className="top-repositories">
        <div className="section-heading">
          <div>
            <div className="eyebrow"><Trophy size={16} /> Top checked</div>
            <h2>Most checked MCP repos</h2>
          </div>
          <span>Confidence is from the latest saved report.</span>
        </div>
        {topRepositoriesError ? <p className="error">{topRepositoriesError}</p> : null}
        {topRepositories.length ? (
          <div className="top-list">
            {topRepositories.map((repo, index) => (
              <a className="top-row" href={`/reports/${encodeURIComponent(repo.latestReportId)}`} key={repo.repoName}>
                <span className="rank">{index + 1}</span>
                <span className="repo-name">{repo.repoName}</span>
                <span>{repo.checkCount} {repo.checkCount === 1 ? "check" : "checks"}</span>
                <span>{Math.round(repo.confidence * 100)}% confidence</span>
                <span>{repo.overallScore}/100</span>
              </a>
            ))}
          </div>
        ) : topRepositoriesError ? null : (
          <p>No MCP repository checks have been saved yet.</p>
        )}
      </section>
    </main>
  );
}

function ScoreCard({ label, score, max }: { label: string; score: number; max: number }) {
  return (
    <div className="score-card">
      <span>{label}</span>
      <strong>{score}</strong>
      <small>/{max}</small>
    </div>
  );
}

function ReportPage({ reportId }: { reportId: string }) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    fetchReport(reportId)
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : "Report not found."))
      .finally(() => setIsLoading(false));
  }, [reportId]);

  const scoreCards = useMemo(() => {
    if (!report) return [];
    return [
      ["Documentation", report.scores.documentation, 20],
      ["Installability", report.scores.installability, 15],
      ["MCP Schema Quality", report.scores.schemaQuality, 20],
      ["Security / Permissions", report.scores.security, 20],
      ["Maintenance", report.scores.maintenance, 15],
      ["Tests / Examples", report.scores.testsExamples, 10]
    ] as const;
  }, [report]);

  if (isLoading) {
    return <main className="shell state"><Loader2 className="spin" /> Loading report...</main>;
  }

  if (error || !report) {
    return (
      <main className="shell state">
        <AlertTriangle />
        <h1>Report unavailable</h1>
        <p>{error || "Report not found."}</p>
        <button onClick={() => (window.location.href = "/")}>Analyze another repo</button>
      </main>
    );
  }

  return (
    <main className="shell report">
      <button className="back" onClick={() => (window.location.href = "/")}>New analysis</button>
      <section className="report-header">
        <div>
          <a className="repo-link" href={report.repo.url} target="_blank" rel="noreferrer">
            {report.repo.owner}/{report.repo.name} <ExternalLink size={16} />
          </a>
          <h1>{report.scores.overall}/100</h1>
          <p>{report.repo.description || "No repository description found."}</p>
        </div>
        <div className={riskClass(report.risk.level)}>{report.risk.level} risk</div>
      </section>

      <section className="metadata">
        <span>Stars: {report.repo.stars}</span>
        <span>Forks: {report.repo.forks}</span>
        <span>Default branch: {report.repo.defaultBranch}</span>
        <span>License: {report.repo.license || "Unknown"}</span>
        <span>Latest commit: {report.repo.lastCommitDate || "Unknown"}</span>
      </section>

      <section className="mcp-status">
        <strong>{report.mcpDetection.isLikelyMcpServer ? "Likely MCP server" : "This does not look like an MCP server"}</strong>
        <span>Confidence {Math.round(report.mcpDetection.confidence * 100)}%</span>
        <ul>
          {report.mcpDetection.evidence.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>

      <section className="score-grid">
        {scoreCards.map(([label, score, max]) => <ScoreCard key={label} label={label} score={score} max={max} />)}
      </section>

      <section>
        <h2>Detected tools</h2>
        {report.mcpDetection.detectedCapabilities.tools.length ? (
          <div className="table">
            {report.mcpDetection.detectedCapabilities.tools.map((tool) => (
              <div className="table-row" key={tool.name}>
                <strong>{tool.name}</strong>
                <span>{tool.description || "No static description found"}</span>
                <span>{tool.hasInputSchema ? "Schema detected" : "No schema detected"}</span>
                <span className={riskClass(tool.riskLevel)}>{tool.riskLevel}</span>
              </div>
            ))}
          </div>
        ) : <p>No tools were detected from static patterns.</p>}
      </section>

      <section>
        <h2>Findings</h2>
        {report.findings.length ? report.findings.map((finding) => (
          <article className="finding" key={`${finding.category}-${finding.title}`}>
            <span>{finding.severity}</span>
            <strong>{finding.title}</strong>
            <p>{finding.description}</p>
            <small>{finding.recommendation}</small>
          </article>
        )) : <p>No major findings were generated.</p>}
      </section>

      <section>
        <h2>Recommended fixes</h2>
        <ul className="fixes">
          {report.recommendedFixes.map((fix) => <li key={fix}>{fix}</li>)}
        </ul>
      </section>

      <section className="configs">
        <h2>Generated client configs</h2>
        <p>Best-effort suggestions. Review commands, args, and environment variables before use.</p>
        <pre>{report.clientConfigs.claudeDesktop}</pre>
      </section>
    </main>
  );
}

export function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const listener = () => setPath(window.location.pathname);
    window.addEventListener("popstate", listener);
    return () => window.removeEventListener("popstate", listener);
  }, []);

  const match = path.match(/^\/reports\/([^/]+)$/);
  if (match) {
    return <ReportPage reportId={decodeURIComponent(match[1])} />;
  }
  return <HomePage />;
}
