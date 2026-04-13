import { useQuery } from "@tanstack/react-query";
import type { CSSProperties } from "react";
import { Link } from "react-router-dom";
import { MetricCard } from "../../components/workspace/MetricCard";
import { ProjectTable } from "../../components/workspace/ProjectTable";
import { SectionCard } from "../../components/workspace/SectionCard";
import { StatusBadge } from "../../components/workspace/StatusBadge";
import { getConfigStatus, listProjects } from "../../services/api";
import { useRuntimeSettings } from "../../app/runtime";

const pipelineStages = [
  "Opportunity",
  "EvaluationRun",
  "Evidence Ledger",
  "Score Ledger",
  "Gate",
  "Report / PRD",
];

export function DashboardPage() {
  const { apiBaseUrl } = useRuntimeSettings();
  const projectsQuery = useQuery({
    queryKey: ["projects", apiBaseUrl],
    queryFn: () => listProjects(apiBaseUrl),
  });
  const configQuery = useQuery({
    queryKey: ["config-status", apiBaseUrl],
    queryFn: () => getConfigStatus(apiBaseUrl),
  });

  const projects = projectsQuery.data?.projects || [];
  const evaluatingCount = projects.filter((project) => project.status === "evaluating").length;
  const completedCount = projects.filter((project) => project.status === "completed").length;
  const reportCount = projects.filter((project) => project.latest_report_id).length;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <div className="hero-panel__copy">
          <span className="eyebrow">Official workspace preview</span>
          <h2>把热点判断变成可审计的商业决策链路</h2>
          <p>
            Gem Cutter 正式版工作台围绕证据账本、评分账本、决策门和 PRD 产物组织界面。
            用户不再面对单页 JSON 调试板，而是在一个可复盘的评估指挥台中推进机会。
          </p>
          <div className="hero-panel__actions">
            <Link className="button-primary" to="/projects">
              进入机会项目
            </Link>
            <Link className="button-ghost" to="/settings">
              检查系统配置
            </Link>
          </div>
        </div>
        <div className="hero-orbit" aria-label="评估链路">
          {pipelineStages.map((stage, index) => (
            <span key={stage} style={{ "--i": index } as CSSProperties}>
              {stage}
            </span>
          ))}
        </div>
      </section>

      <div className="metric-grid">
        <MetricCard label="机会项目" value={projects.length} helper="已创建项目总数" accent="teal" />
        <MetricCard label="评估中" value={evaluatingCount} helper="正在运行或等待结果" accent="amber" />
        <MetricCard label="已完成" value={completedCount} helper="形成 gate 决策" accent="ink" />
        <MetricCard label="报告产物" value={reportCount} helper="可审阅报告/PRD" accent="red" />
      </div>

      <div className="dashboard-grid">
        <SectionCard
          title="最近机会"
          kicker="Project Ledger"
          action={<Link to="/projects">查看全部</Link>}
        >
          <ProjectTable projects={projects.slice(0, 5)} />
        </SectionCard>

        <SectionCard title="系统状态" kicker="Runtime">
          <div className="status-list">
            <div>
              <span>LLM Provider</span>
              <StatusBadge value={configQuery.data?.llm_provider || "unknown"} tone="info" />
            </div>
            <div>
              <span>Search Provider</span>
              <StatusBadge value={configQuery.data?.search_provider || "unknown"} tone="neutral" />
            </div>
            <div>
              <span>Ark API</span>
              <StatusBadge value={configQuery.data?.ark.configured ? "configured" : "not_configured"} />
            </div>
            <div>
              <span>Evidence per dimension</span>
              <strong>{configQuery.data?.search.evidence_per_dimension ?? "-"}</strong>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
