export type RiskLevel = "Low" | "Medium" | "High";

export interface AnalyzeResponse {
  reportId: string;
  status: "completed";
  summary: {
    overallScore: number;
    riskLevel: RiskLevel;
    repoName: string;
  };
}

export interface ConfigAnalyzeResult {
  serverName: string;
  repoUrl?: string | null;
  healthCheckUrl?: string | null;
  responseCode?: number | null;
  responseError?: string | null;
  reportId?: string | null;
  status: "completed" | "validated" | "failed" | "skipped";
  summary?: AnalyzeResponse["summary"] | null;
  error?: string | null;
}

export interface AnalyzeConfigResponse {
  results: ConfigAnalyzeResult[];
}

export interface TopRepository {
  repoUrl: string;
  repoName: string;
  checkCount: number;
  confidence: number;
  overallScore: number;
  riskLevel: RiskLevel;
  latestReportId: string;
}

export interface ToolInfo {
  name: string;
  description: string;
  hasInputSchema: boolean;
  riskLevel: RiskLevel;
}

export interface Finding {
  severity: "info" | "warning" | "critical";
  category: string;
  title: string;
  description: string;
  recommendation: string;
}

export interface Report {
  id: string;
  repo: {
    url: string;
    owner: string;
    name: string;
    description: string;
    stars: number;
    forks: number;
    defaultBranch: string;
    lastCommitDate: string;
    license: string;
    detectedLanguages: string[];
  };
  mcpDetection: {
    isLikelyMcpServer: boolean;
    confidence: number;
    evidence: string[];
    detectedCapabilities: {
      tools: ToolInfo[];
      resources: unknown[];
      prompts: unknown[];
    };
  };
  scores: {
    documentation: number;
    installability: number;
    schemaQuality: number;
    security: number;
    maintenance: number;
    testsExamples: number;
    overall: number;
  };
  risk: {
    level: RiskLevel;
    reasons: string[];
  };
  findings: Finding[];
  recommendedFixes: string[];
  clientConfigs: {
    claudeDesktop: string;
    cursor: string;
  };
  analysisLimits?: {
    fetchedFiles: number;
    skipped: string[];
  };
}
