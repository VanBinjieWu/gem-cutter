import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { ProjectDetailPage } from "../pages/projects/detail/ProjectDetailPage";
import { ProjectsPage } from "../pages/projects/ProjectsPage";
import { ReportsPage } from "../pages/reports/ReportsPage";
import { RunsPage } from "../pages/runs/RunsPage";
import { SettingsPage } from "../pages/settings/SettingsPage";

function NotFoundPage() {
  return (
    <div className="empty-state">
      <strong>页面不存在</strong>
      <p>请从左侧导航重新进入工作台。</p>
    </div>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

