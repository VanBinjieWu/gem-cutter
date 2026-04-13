import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet } from "react-router-dom";
import { navigationItems } from "../constants/navigation";
import { getConfigStatus } from "../services/api";
import { useRuntimeSettings } from "../app/runtime";
import { StatusBadge } from "../components/workspace/StatusBadge";

export function AppShell() {
  const { apiBaseUrl } = useRuntimeSettings();
  const configQuery = useQuery({
    queryKey: ["config-status", apiBaseUrl],
    queryFn: () => getConfigStatus(apiBaseUrl),
  });

  const config = configQuery.data;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark" aria-label="Gem Cutter">
          <span>GC</span>
          <div>
            <strong>Gem Cutter</strong>
            <small>Evidence command center</small>
          </div>
        </div>

        <nav className="nav-list" aria-label="主导航">
          {navigationItems.map((item) => (
            <NavLink className="nav-item" to={item.path} key={item.path}>
              <span>{item.label}</span>
              <small>{item.description}</small>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-card">
          <span className="eyebrow">Provider</span>
          <div className="sidebar-card__providers">
            <StatusBadge value={config?.llm_provider || "loading"} tone="info" />
            <StatusBadge value={config?.search_provider || "loading"} tone="neutral" />
          </div>
          <p>{config?.ark.configured ? "Ark 已配置，可执行真实搜索。" : "当前使用 mock/fallback 模式。"}</p>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Commercial evaluation workspace</span>
            <h1>证据驱动的机会评估平台</h1>
          </div>
          <div className="topbar__status">
            <span>{apiBaseUrl}</span>
            <StatusBadge value={configQuery.isError ? "disconnected" : "connected"} tone={configQuery.isError ? "danger" : "success"} />
          </div>
        </header>

        <main className="page-frame">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

