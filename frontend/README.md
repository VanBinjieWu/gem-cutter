# Gem Cutter Frontend

Official frontend workspace for Gem Cutter, built with React, Vite, and TypeScript.

## Run

```powershell
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The backend defaults to:

```text
http://127.0.0.1:8000
```

You can change the API base URL from the Settings page. The value is stored in local browser storage.

## Architecture

```text
src/
  app/          global providers and route composition
  layouts/      AppShell and workspace framing
  pages/        route-level orchestration
  components/   reusable workspace and chart components
  services/     backend API client
  types/        backend-aligned TypeScript types
  constants/    navigation and static app metadata
  styles/       design tokens and global CSS
```

The legacy static demo is preserved at:

```text
frontend/legacy/mvp-demo.html
```

