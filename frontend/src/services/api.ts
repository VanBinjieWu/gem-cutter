import type {
  ApiEvidenceResponse,
  ApiListProjectsResponse,
  ApiLogsResponse,
  ApiProjectResponse,
  ApiReportResponse,
  ApiRunResponse,
  ApiScoresResponse,
  ConfigStatus,
  EvaluationView,
} from "../types/api";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function normalizeBaseUrl(apiBaseUrl: string) {
  return apiBaseUrl.replace(/\/$/, "");
}

export function buildApiUrl(apiBaseUrl: string, path: string) {
  return `${normalizeBaseUrl(apiBaseUrl)}${path}`;
}

async function readError(response: Response) {
  const text = await response.text();
  try {
    const parsed = JSON.parse(text) as { detail?: string };
    return parsed.detail || text || response.statusText;
  } catch {
    return text || response.statusText;
  }
}

async function requestJson<T>(apiBaseUrl: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${normalizeBaseUrl(apiBaseUrl)}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  return response.json() as Promise<T>;
}

async function requestText(apiBaseUrl: string, path: string): Promise<string> {
  const response = await fetch(`${normalizeBaseUrl(apiBaseUrl)}${path}`);
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status);
  }
  return response.text();
}

export function getConfigStatus(apiBaseUrl: string) {
  return requestJson<ConfigStatus>(apiBaseUrl, "/api/config/status");
}

export function listProjects(apiBaseUrl: string) {
  return requestJson<ApiListProjectsResponse>(apiBaseUrl, "/api/projects");
}

export function getProject(apiBaseUrl: string, projectId: string) {
  return requestJson<ApiProjectResponse>(apiBaseUrl, `/api/projects/${projectId}`);
}

export function createProject(
  apiBaseUrl: string,
  payload: {
    title: string;
    input_topic: string;
    target_market?: string;
    target_user_hint?: string;
    constraints?: Record<string, unknown>;
  },
) {
  return requestJson<ApiProjectResponse>(apiBaseUrl, "/api/projects", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function startEvaluation(apiBaseUrl: string, projectId: string) {
  return requestJson<ApiRunResponse>(apiBaseUrl, `/api/projects/${projectId}/evaluations`, {
    method: "POST",
  });
}

export function getRun(apiBaseUrl: string, runId: string) {
  return requestJson<ApiRunResponse>(apiBaseUrl, `/api/evaluations/${runId}`);
}

export function getEvaluationView(apiBaseUrl: string, runId: string) {
  return requestJson<EvaluationView>(apiBaseUrl, `/api/evaluations/${runId}/view`);
}

export function listEvidence(apiBaseUrl: string, runId: string) {
  return requestJson<ApiEvidenceResponse>(apiBaseUrl, `/api/evaluations/${runId}/evidence`);
}

export function listScores(apiBaseUrl: string, runId: string) {
  return requestJson<ApiScoresResponse>(apiBaseUrl, `/api/evaluations/${runId}/scores`);
}

export function listLlmLogs(apiBaseUrl: string, runId: string) {
  return requestJson<ApiLogsResponse>(apiBaseUrl, `/api/evaluations/${runId}/llm-logs`);
}

export function generatePrd(apiBaseUrl: string, runId: string) {
  return requestJson<ApiReportResponse>(apiBaseUrl, `/api/evaluations/${runId}/prd`, {
    method: "POST",
  });
}

export function getReport(apiBaseUrl: string, reportId: string) {
  return requestJson<ApiReportResponse>(apiBaseUrl, `/api/reports/${reportId}`);
}

export function getReportMarkdown(apiBaseUrl: string, reportId: string) {
  return requestText(apiBaseUrl, `/api/reports/${reportId}/markdown`);
}

export function getEvaluationStreamUrl(apiBaseUrl: string, runId: string) {
  return buildApiUrl(apiBaseUrl, `/api/evaluations/${runId}/stream`);
}
