import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { MetricCard } from "../../components/workspace/MetricCard";
import { SectionCard } from "../../components/workspace/SectionCard";
import { StatusBadge } from "../../components/workspace/StatusBadge";
import { listProjects } from "../../services/api";
import { useRuntimeSettings } from "../../app/runtime";

export function RunsPage() {
  const { apiBaseUrl } = useRuntimeSettings();
  const projectsQuery = useQuery({
    queryKey: ["projects", apiBaseUrl],
    queryFn: () => listProjects(apiBaseUrl),
  });

  const projects = projectsQuery.data?.projects || [];
  const projectsWithRuns = projects.filter((project) => project.latest_evaluation_run_id);
  const runningProjects = projects.filter((project) => project.status === "evaluating");
  const failedProjects = projects.filter((project) => project.status === "failed");

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Evaluation Runs</span>
          <h2>运行中心</h2>
          <p>当前后端尚未提供全量 run index，首版先从项目最近运行聚合展示。</p>
        </div>
      </div>

      <div className="metric-grid">
        <MetricCard label="最近运行" value={projectsWithRuns.length} helper="latest_evaluation_run_id" />
        <MetricCard label="运行中" value={runningProjects.length} helper="project.status=evaluating" accent="amber" />
        <MetricCard label="失败项目" value={failedProjects.length} helper="需要复盘错误" accent="red" />
        <MetricCard label="待补接口" value="GET /api/evaluations" helper="后端 roadmap" accent="ink" />
      </div>

      <SectionCard title="最近评估运行" kicker="Run Index">
        <div className="run-list">
          {projectsWithRuns.length ? (
            projectsWithRuns.map((project) => (
              <Link className="run-card" to={`/projects/${project.id}`} key={project.id}>
                <div>
                  <strong>{project.title}</strong>
                  <small>{project.latest_evaluation_run_id}</small>
                </div>
                <StatusBadge value={project.status} />
              </Link>
            ))
          ) : (
            <div className="empty-state">
              <strong>暂无运行记录</strong>
              <p>创建机会项目并启动评估后，这里会展示最近运行。</p>
            </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

