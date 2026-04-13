import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { SectionCard } from "../../components/workspace/SectionCard";
import { StatusBadge } from "../../components/workspace/StatusBadge";
import { DEFAULT_API_BASE_URL, useRuntimeSettings } from "../../app/runtime";
import { getConfigStatus } from "../../services/api";

export function SettingsPage() {
  const { apiBaseUrl, setApiBaseUrl } = useRuntimeSettings();
  const [draftApiBaseUrl, setDraftApiBaseUrl] = useState(apiBaseUrl);
  const configQuery = useQuery({
    queryKey: ["config-status", apiBaseUrl],
    queryFn: () => getConfigStatus(apiBaseUrl),
  });

  const config = configQuery.data;

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow">Runtime Settings</span>
          <h2>系统设置</h2>
          <p>只展示非敏感运行信息。Ark API Key 仍由后端配置文件或环境变量管理。</p>
        </div>
      </div>

      <div className="settings-grid">
        <SectionCard title="API 连接" kicker="Frontend Runtime">
          <form
            className="project-form"
            onSubmit={(event) => {
              event.preventDefault();
              setApiBaseUrl(draftApiBaseUrl);
            }}
          >
            <label>
              API Base URL
              <input value={draftApiBaseUrl} onChange={(event) => setDraftApiBaseUrl(event.target.value)} />
            </label>
            <div className="button-row">
              <button className="button-primary">保存</button>
              <button
                className="button-ghost"
                type="button"
                onClick={() => {
                  setDraftApiBaseUrl(DEFAULT_API_BASE_URL);
                  setApiBaseUrl(DEFAULT_API_BASE_URL);
                }}
              >
                恢复默认
              </button>
            </div>
          </form>
        </SectionCard>

        <SectionCard title="Provider 状态" kicker="Backend Config">
          <div className="status-list">
            <div>
              <span>连接状态</span>
              <StatusBadge value={configQuery.isError ? "disconnected" : "connected"} tone={configQuery.isError ? "danger" : "success"} />
            </div>
            <div>
              <span>LLM Provider</span>
              <StatusBadge value={config?.llm_provider || "unknown"} tone="info" />
            </div>
            <div>
              <span>Search Provider</span>
              <StatusBadge value={config?.search_provider || "unknown"} />
            </div>
            <div>
              <span>Ark Configured</span>
              <StatusBadge value={config?.ark.configured ? "configured" : "not_configured"} />
            </div>
            <div>
              <span>Model</span>
              <strong>{config?.ark.model || "-"}</strong>
            </div>
            <div>
              <span>Stream</span>
              <strong>{String(config?.ark.stream ?? "-")}</strong>
            </div>
            <div>
              <span>Tool Choice</span>
              <strong>{String(config?.ark.enable_tool_choice ?? "-")}</strong>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}

