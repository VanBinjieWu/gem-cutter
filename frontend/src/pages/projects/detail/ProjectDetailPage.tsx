import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { EvidenceBoard } from "../../../components/workspace/EvidenceBoard";
import { LlmLogPanel } from "../../../components/workspace/LlmLogPanel";
import { MetricCard } from "../../../components/workspace/MetricCard";
import { ReportPanel } from "../../../components/workspace/ReportPanel";
import { RunTimeline } from "../../../components/workspace/RunTimeline";
import { ScoreLedgerPanel } from "../../../components/workspace/ScoreLedgerPanel";
import { SectionCard } from "../../../components/workspace/SectionCard";
import { StatusBadge } from "../../../components/workspace/StatusBadge";
import {
  generatePrd,
  getEvaluationStreamUrl,
  getEvaluationView,
  getProject,
  getReportMarkdown,
  listEvidence,
  listLlmLogs,
  startEvaluation,
} from "../../../services/api";
import { useRuntimeSettings } from "../../../app/runtime";
import type { EvaluationEvent } from "../../../types/api";

type WorkspaceTab = "overview" | "evidence" | "reports" | "logs";

function parseSsePayload(data: string): EvaluationEvent | null {
  try {
    return JSON.parse(data) as EvaluationEvent;
  } catch {
    return null;
  }
}

export function ProjectDetailPage() {
  const { projectId = "" } = useParams();
  const { apiBaseUrl } = useRuntimeSettings();
  const queryClient = useQueryClient();
  const [selectedDimension, setSelectedDimension] = useState("");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState("");
  const [selectedReportId, setSelectedReportId] = useState("");
  const [events, setEvents] = useState<EvaluationEvent[]>([]);
  const [activeTab, setActiveTab] = useState<WorkspaceTab>("overview");

  const projectQuery = useQuery({
    queryKey: ["project", apiBaseUrl, projectId],
    queryFn: () => getProject(apiBaseUrl, projectId),
    enabled: Boolean(projectId),
  });

  const project = projectQuery.data?.project;
  const runId = project?.latest_evaluation_run_id || "";

  const viewQuery = useQuery({
    queryKey: ["evaluation-view", apiBaseUrl, runId],
    queryFn: () => getEvaluationView(apiBaseUrl, runId),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.run.status;
      return status === "running" || status === "pending" ? 2500 : false;
    },
  });

  const evidenceQuery = useQuery({
    queryKey: ["evidence", apiBaseUrl, runId],
    queryFn: () => listEvidence(apiBaseUrl, runId),
    enabled: Boolean(runId),
    refetchInterval: viewQuery.data?.run.status === "running" ? 3000 : false,
  });

  const logsQuery = useQuery({
    queryKey: ["llm-logs", apiBaseUrl, runId],
    queryFn: () => listLlmLogs(apiBaseUrl, runId),
    enabled: Boolean(runId),
    refetchInterval: viewQuery.data?.run.status === "running" ? 3000 : false,
  });

  const view = viewQuery.data;
  const gate = view?.gate_decision;
  const reports = view?.reports || [];
  const latestReportId = reports[reports.length - 1]?.id || "";
  const activeReportId = selectedReportId || latestReportId;

  const markdownQuery = useQuery({
    queryKey: ["report-markdown", apiBaseUrl, activeReportId],
    queryFn: () => getReportMarkdown(apiBaseUrl, activeReportId),
    enabled: Boolean(activeReportId),
  });

  useEffect(() => {
    if (!selectedReportId && latestReportId) {
      setSelectedReportId(latestReportId);
    }
  }, [latestReportId, selectedReportId]);

  useEffect(() => {
    if (!runId || view?.run.status !== "running") {
      return undefined;
    }

    const source = new EventSource(getEvaluationStreamUrl(apiBaseUrl, runId));

    const handleMessage = (event: MessageEvent<string>) => {
      const parsed = parseSsePayload(event.data);
      if (!parsed) return;
      setEvents((current) => {
        if (current.some((item) => item.id === parsed.id)) {
          return current;
        }
        return [...current.slice(-60), parsed];
      });
      void queryClient.invalidateQueries({ queryKey: ["evaluation-view", apiBaseUrl, runId] });
      void queryClient.invalidateQueries({ queryKey: ["evidence", apiBaseUrl, runId] });
      void queryClient.invalidateQueries({ queryKey: ["llm-logs", apiBaseUrl, runId] });
    };

    source.onmessage = handleMessage;
    [
      "evaluation.started",
      "plan.created",
      "evidence.search_started",
      "raw_signal.added",
      "evidence.added",
      "evidence.clustered",
      "score.updated",
      "gate.decided",
      "report.generated",
      "prd.generated",
      "evaluation.completed",
      "evaluation.failed",
    ].forEach((eventName) => source.addEventListener(eventName, handleMessage as EventListener));

    return () => {
      source.close();
    };
  }, [apiBaseUrl, queryClient, runId, view?.run.status]);

  const startMutation = useMutation({
    mutationFn: () => startEvaluation(apiBaseUrl, projectId),
    onSuccess: async (result) => {
      setEvents([]);
      setSelectedDimension("");
      setSelectedEvidenceId("");
      setSelectedReportId("");
      await queryClient.invalidateQueries({ queryKey: ["project", apiBaseUrl, projectId] });
      await queryClient.invalidateQueries({ queryKey: ["evaluation-view", apiBaseUrl, result.run.id] });
    },
  });

  const prdMutation = useMutation({
    mutationFn: () => generatePrd(apiBaseUrl, runId),
    onSuccess: async (result) => {
      setSelectedReportId(result.report.id);
      setActiveTab("reports");
      await queryClient.invalidateQueries({ queryKey: ["evaluation-view", apiBaseUrl, runId] });
      await queryClient.invalidateQueries({ queryKey: ["report-markdown", apiBaseUrl, result.report.id] });
    },
  });

  const canGeneratePrd = Boolean(runId && gate && ["go", "conditional_go"].includes(gate.action));
  const evidence = evidenceQuery.data?.evidence || [];
  const logs = logsQuery.data?.logs || [];
  const scoreDimensions = view?.score_summary.dimensions || [];

  const evidenceByDimension = useMemo(() => {
    return scoreDimensions.map((score) => ({
      dimension: score.dimension,
      evidenceCount: evidence.filter((item) => item.dimension === score.dimension).length,
      score: score.score,
      confidence: score.confidence,
    }));
  }, [evidence, scoreDimensions]);

  if (projectQuery.isLoading) {
    return <div className="loading-panel">正在加载项目...</div>;
  }

  if (!project) {
    return (
      <div className="empty-state">
        <strong>项目不存在</strong>
        <p>请返回项目列表重新选择。</p>
        <Link className="button-primary" to="/projects">
          返回项目列表
        </Link>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <div className="project-hero">
        <div>
          <span className="eyebrow">Project Workspace</span>
          <h2>{project.title}</h2>
          <p>{project.input_topic}</p>
          <div className="hero-tags">
            <StatusBadge value={project.status} />
            <span>{project.target_market || "未指定市场"}</span>
            <span>{project.target_user_hint || "未指定用户"}</span>
            {runId ? <span>{runId}</span> : null}
          </div>
        </div>
        <div className="project-hero__actions">
          <button className="button-ghost" onClick={() => startMutation.mutate()} disabled={startMutation.isPending}>
            {startMutation.isPending ? "启动中..." : runId ? "重新评估" : "启动评估"}
          </button>
          <button
            className="button-primary"
            disabled={!canGeneratePrd || prdMutation.isPending}
            onClick={() => prdMutation.mutate()}
          >
            {prdMutation.isPending ? "生成中..." : "生成 PRD"}
          </button>
        </div>
      </div>

      <div className="metric-grid">
        <MetricCard label="Gate" value={gate?.action || "-"} helper={gate?.reason || "等待门禁决策"} accent="amber" />
        <MetricCard label="总分" value={gate?.total_score ?? "-"} helper="后端复算加权分" accent="teal" />
        <MetricCard label="置信度" value={gate?.confidence ?? "-"} helper="受证据覆盖限制" accent="ink" />
        <MetricCard
          label="证据覆盖"
          value={`${view?.evidence_summary.valid_evidence_count ?? 0}/${view?.evidence_summary.raw_signal_count ?? 0}`}
          helper="valid evidence / raw signals"
          accent="red"
        />
      </div>

      <div className="workspace-tabs">
        {[
          ["overview", "总览"],
          ["evidence", "证据审阅"],
          ["reports", "报告 / PRD"],
          ["logs", "模型日志"],
        ].map(([key, label]) => (
          <button
            className={activeTab === key ? "workspace-tab is-active" : "workspace-tab"}
            key={key}
            onClick={() => setActiveTab(key as WorkspaceTab)}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" ? (
        <div className="project-grid project-grid--overview">
          <SectionCard title="运行阶段" kicker="Timeline">
            <RunTimeline run={view?.run} events={events} />
          </SectionCard>

          <SectionCard title="评分账本" kicker="Score Ledger">
            <ScoreLedgerPanel
              gate={gate}
              scores={scoreDimensions}
              selectedDimension={selectedDimension}
              onSelectDimension={(dimension) => {
                setSelectedDimension(dimension);
                setActiveTab(dimension ? "evidence" : "overview");
              }}
            />
          </SectionCard>

          <SectionCard title="证据覆盖矩阵" kicker="Coverage">
            <div className="coverage-matrix">
              {evidenceByDimension.length ? (
                evidenceByDimension.map((item) => (
                  <button
                    key={item.dimension}
                    className={selectedDimension === item.dimension ? "coverage-cell is-active" : "coverage-cell"}
                    onClick={() => {
                      setSelectedDimension(item.dimension);
                      setActiveTab("evidence");
                    }}
                  >
                    <strong>{item.dimension}</strong>
                    <span>{item.evidenceCount} evidence</span>
                    <small>
                      score {item.score.toFixed(0)} · conf {item.confidence}
                    </small>
                  </button>
                ))
              ) : (
                <div className="empty-state compact">
                  <strong>等待证据覆盖</strong>
                  <p>评分完成后会按维度展示覆盖情况。</p>
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard title="下一步动作" kicker="Decision">
            <div className="next-steps">
              {(gate?.next_steps || ["等待系统完成评估并生成 GateDecision。"]).map((step) => (
                <div key={step}>
                  <span />
                  <p>{step}</p>
                </div>
              ))}
            </div>
            {prdMutation.isError ? <p className="form-error">{String(prdMutation.error.message)}</p> : null}
          </SectionCard>
        </div>
      ) : null}

      {activeTab === "evidence" ? (
        <SectionCard
          title="证据审阅"
          kicker="Evidence Ledger"
          action={selectedDimension ? <StatusBadge value={selectedDimension} tone="info" /> : <StatusBadge value="all dimensions" />}
        >
          <EvidenceBoard
            evidence={evidence}
            selectedDimension={selectedDimension}
            selectedEvidenceId={selectedEvidenceId}
            onSelectEvidence={setSelectedEvidenceId}
          />
        </SectionCard>
      ) : null}

      {activeTab === "reports" ? (
        <SectionCard title="报告与 PRD" kicker="Artifacts">
          <ReportPanel
            reports={reports}
            selectedReportId={activeReportId}
            onSelectReport={setSelectedReportId}
            markdown={markdownQuery.data}
            isLoading={markdownQuery.isLoading}
          />
        </SectionCard>
      ) : null}

      {activeTab === "logs" ? (
        <SectionCard title="模型日志" kicker="LLM Trace">
          <LlmLogPanel logs={logs} />
        </SectionCard>
      ) : null}
    </div>
  );
}

