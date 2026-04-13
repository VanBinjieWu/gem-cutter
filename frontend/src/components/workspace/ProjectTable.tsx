import { Link } from "react-router-dom";
import { StatusBadge } from "./StatusBadge";
import type { OpportunityProject } from "../../types/api";

interface ProjectTableProps {
  projects: OpportunityProject[];
}

export function ProjectTable({ projects }: ProjectTableProps) {
  if (!projects.length) {
    return (
      <div className="empty-state">
        <strong>还没有机会项目</strong>
        <p>创建第一个评估项目后，这里会展示项目状态、最近运行和报告入口。</p>
      </div>
    );
  }

  return (
    <div className="data-table" role="table" aria-label="机会项目列表">
      <div className="data-table__row data-table__row--head" role="row">
        <span>项目</span>
        <span>市场</span>
        <span>状态</span>
        <span>最近运行</span>
      </div>
      {projects.map((project) => (
        <Link className="data-table__row data-table__row--link" to={`/projects/${project.id}`} key={project.id}>
          <span>
            <strong>{project.title}</strong>
            <small>{project.input_topic}</small>
          </span>
          <span>{project.target_market || "未指定"}</span>
          <span>
            <StatusBadge value={project.status} />
          </span>
          <span>{project.latest_evaluation_run_id || "尚未运行"}</span>
        </Link>
      ))}
    </div>
  );
}

