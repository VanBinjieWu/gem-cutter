import { useDeferredValue, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { ProjectTable } from "../../components/workspace/ProjectTable";
import { SectionCard } from "../../components/workspace/SectionCard";
import { StatusBadge } from "../../components/workspace/StatusBadge";
import { createProject, listProjects, startEvaluation } from "../../services/api";
import { useRuntimeSettings } from "../../app/runtime";

export function ProjectsPage() {
  const { apiBaseUrl } = useRuntimeSettings();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [form, setForm] = useState({
    title: "AI 视频脚本生成工具",
    input_topic: "AI video script generation tool for creators",
    target_market: "China independent creators and small teams",
    target_user_hint: "短视频创作者、内容运营、小型营销团队",
  });

  const projectsQuery = useQuery({
    queryKey: ["projects", apiBaseUrl],
    queryFn: () => listProjects(apiBaseUrl),
  });

  const createAndRunMutation = useMutation({
    mutationFn: async () => {
      const created = await createProject(apiBaseUrl, form);
      await startEvaluation(apiBaseUrl, created.project.id);
      return created.project;
    },
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ["projects", apiBaseUrl] });
      navigate(`/projects/${project.id}`);
    },
  });

  const projects = projectsQuery.data?.projects || [];
  const keyword = deferredSearch.trim().toLowerCase();
  const filteredProjects = keyword
    ? projects.filter((project) =>
        `${project.title} ${project.input_topic} ${project.target_market || ""}`.toLowerCase().includes(keyword),
      )
    : projects;

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Opportunity Projects</span>
          <h2>机会项目</h2>
          <p>正式版前端以项目为上下文承载每一次评估、证据、评分、门禁和产物。</p>
        </div>
        <StatusBadge value={`${projects.length} projects`} tone="neutral" />
      </div>

      <div className="split-grid split-grid--form">
        <SectionCard title="创建并启动评估" kicker="New Evaluation">
          <form
            className="project-form"
            onSubmit={(event) => {
              event.preventDefault();
              createAndRunMutation.mutate();
            }}
          >
            <label>
              项目标题
              <input
                value={form.title}
                onChange={(event) => setForm({ ...form, title: event.target.value })}
              />
            </label>
            <label>
              热点/想法
              <textarea
                value={form.input_topic}
                onChange={(event) => setForm({ ...form, input_topic: event.target.value })}
              />
            </label>
            <label>
              目标市场
              <input
                value={form.target_market}
                onChange={(event) => setForm({ ...form, target_market: event.target.value })}
              />
            </label>
            <label>
              目标用户线索
              <input
                value={form.target_user_hint}
                onChange={(event) => setForm({ ...form, target_user_hint: event.target.value })}
              />
            </label>
            <button className="button-primary" disabled={createAndRunMutation.isPending}>
              {createAndRunMutation.isPending ? "正在创建评估..." : "创建并启动评估"}
            </button>
            {createAndRunMutation.isError ? (
              <p className="form-error">{String(createAndRunMutation.error.message)}</p>
            ) : null}
          </form>
        </SectionCard>

        <SectionCard title="浏览项目" kicker="Project Ledger" action={<Link to="/runs">运行中心</Link>}>
          <div className="toolbar">
            <input
              placeholder="搜索标题、主题或市场..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
          <ProjectTable projects={filteredProjects} />
        </SectionCard>
      </div>
    </div>
  );
}

