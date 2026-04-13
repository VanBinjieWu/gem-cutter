import ReactMarkdown from "react-markdown";
import { StatusBadge } from "./StatusBadge";
import type { EvaluationReport } from "../../types/api";

interface ReportPanelProps {
  reports: EvaluationReport[];
  markdown?: string;
  selectedReportId: string;
  onSelectReport: (reportId: string) => void;
  isLoading?: boolean;
}

export function ReportPanel({ reports, markdown, selectedReportId, onSelectReport, isLoading }: ReportPanelProps) {
  return (
    <div className="report-workbench">
      <div className="report-switcher">
        {reports.length ? (
          reports.map((report) => (
            <button
              className={selectedReportId === report.id ? "report-pill is-active" : "report-pill"}
              onClick={() => onSelectReport(report.id)}
              key={report.id}
            >
              <StatusBadge value={report.report_type} tone="info" />
              <span>{report.title}</span>
            </button>
          ))
        ) : (
          <div className="empty-state compact">
            <strong>暂无报告</strong>
            <p>评估完成后会生成 Evaluation Report。</p>
          </div>
        )}
      </div>
      <article className="markdown-viewer markdown-viewer--embedded">
        {isLoading ? <p>正在加载报告...</p> : null}
        {markdown ? <ReactMarkdown>{markdown}</ReactMarkdown> : <p>请选择报告进行预览。</p>}
      </article>
    </div>
  );
}

