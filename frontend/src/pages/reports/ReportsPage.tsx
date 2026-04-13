import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { Link } from "react-router-dom";
import { SectionCard } from "../../components/workspace/SectionCard";
import { StatusBadge } from "../../components/workspace/StatusBadge";
import { getReport, getReportMarkdown, listProjects } from "../../services/api";
import { useRuntimeSettings } from "../../app/runtime";

export function ReportsPage() {
  const { apiBaseUrl } = useRuntimeSettings();
  const [selectedReportId, setSelectedReportId] = useState("");

  const projectsQuery = useQuery({
    queryKey: ["projects", apiBaseUrl],
    queryFn: () => listProjects(apiBaseUrl),
  });

  const reports = (projectsQuery.data?.projects || [])
    .filter((project) => project.latest_report_id)
    .map((project) => ({
      projectId: project.id,
      projectTitle: project.title,
      reportId: project.latest_report_id || "",
      updatedAt: project.updated_at,
    }));

  useEffect(() => {
    if (!selectedReportId && reports[0]?.reportId) {
      setSelectedReportId(reports[0].reportId);
    }
  }, [reports, selectedReportId]);

  const reportQuery = useQuery({
    queryKey: ["report", apiBaseUrl, selectedReportId],
    queryFn: () => getReport(apiBaseUrl, selectedReportId),
    enabled: Boolean(selectedReportId),
  });

  const markdownQuery = useQuery({
    queryKey: ["report-markdown", apiBaseUrl, selectedReportId],
    queryFn: () => getReportMarkdown(apiBaseUrl, selectedReportId),
    enabled: Boolean(selectedReportId),
  });

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Artifacts</span>
          <h2>产物中心</h2>
          <p>正式版前端将评估报告和 PRD 作为可复盘产物，而不是临时输出。</p>
        </div>
      </div>

      <div className="reports-layout">
        <SectionCard title="报告列表" kicker="Reports">
          <div className="report-list">
            {reports.length ? (
              reports.map((item) => (
                <button
                  className={selectedReportId === item.reportId ? "report-list__item is-active" : "report-list__item"}
                  key={item.reportId}
                  onClick={() => setSelectedReportId(item.reportId)}
                >
                  <strong>{item.projectTitle}</strong>
                  <span>{item.reportId}</span>
                </button>
              ))
            ) : (
              <div className="empty-state compact">
                <strong>暂无报告</strong>
                <p>完成一次评估后，报告会出现在这里。</p>
                <Link className="button-primary" to="/projects">
                  创建项目
                </Link>
              </div>
            )}
          </div>
        </SectionCard>

        <SectionCard
          title={reportQuery.data?.report.title || "报告预览"}
          kicker="Markdown Viewer"
          action={reportQuery.data?.report.report_type ? <StatusBadge value={reportQuery.data.report.report_type} tone="info" /> : null}
        >
          <article className="markdown-viewer">
            {markdownQuery.isLoading ? <p>正在加载 Markdown...</p> : null}
            {markdownQuery.isError ? <p className="form-error">{String(markdownQuery.error.message)}</p> : null}
            {markdownQuery.data ? <ReactMarkdown>{markdownQuery.data}</ReactMarkdown> : null}
            {!selectedReportId ? <p>请选择左侧报告。</p> : null}
          </article>
        </SectionCard>
      </div>
    </div>
  );
}

