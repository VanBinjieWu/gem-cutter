from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from .core.config import load_settings, public_settings
from .domain.models import ReportType, RunStatus
from .domain.services import EvaluationService, ProjectService
from .domain.store import JsonStore


DATA_DIR = Path("data")
SETTINGS = load_settings()
STORE = JsonStore(DATA_DIR / "gem_cutter_store.json")
PROJECTS = ProjectService(STORE)
EVALUATIONS = EvaluationService(
    STORE,
    artifact_dir=DATA_DIR / "reports",
    max_search_workers=SETTINGS.search.max_workers,
    per_dimension_workers=SETTINGS.search.per_dimension_workers,
    evidence_per_dimension=SETTINGS.search.evidence_per_dimension,
    settings=SETTINGS,
)
LOGGER = logging.getLogger(__name__)


class CreateProjectRequest(BaseModel):
    title: str
    input_topic: str
    target_market: Optional[str] = None
    target_user_hint: Optional[str] = None
    constraints: Dict[str, Any] = {}


class CreateProjectResponse(BaseModel):
    project: Dict[str, Any]


class StartEvaluationResponse(BaseModel):
    run: Dict[str, Any]


def run_evaluation_background(run_id: str) -> None:
    try:
        EVALUATIONS.run(run_id)
    except Exception:
        LOGGER.exception("Evaluation background task failed for run %s", run_id)


def create_app() -> FastAPI:
    app = FastAPI(title="Gem Cutter MVP", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/config/status")
    def config_status() -> Dict[str, Any]:
        return public_settings(SETTINGS)

    @app.post("/api/projects", response_model=CreateProjectResponse)
    def create_project(payload: CreateProjectRequest) -> Dict[str, Any]:
        project = PROJECTS.create_project(
            title=payload.title,
            input_topic=payload.input_topic,
            target_market=payload.target_market,
            target_user_hint=payload.target_user_hint,
            constraints=payload.constraints,
        )
        return {"project": project.dict()}

    @app.get("/api/projects")
    def list_projects() -> Dict[str, Any]:
        return {"projects": [item.dict() for item in STORE.list_projects()]}

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> Dict[str, Any]:
        project = STORE.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="project not found")
        return {"project": project.dict()}

    @app.post("/api/projects/{project_id}/evaluations", response_model=StartEvaluationResponse)
    def start_evaluation(project_id: str, background_tasks: BackgroundTasks) -> Dict[str, Any]:
        try:
            run = EVALUATIONS.start_run(project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        background_tasks.add_task(run_evaluation_background, run.id)
        return {"run": run.dict()}

    @app.post("/api/evaluations/{run_id}/run-sync")
    def run_sync(run_id: str) -> Dict[str, Any]:
        try:
            run = EVALUATIONS.run(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"run": run.dict()}

    @app.get("/api/evaluations/{run_id}")
    def get_run(run_id: str) -> Dict[str, Any]:
        run = STORE.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="run not found")
        return {"run": run.dict()}

    @app.get("/api/evaluations/{run_id}/view")
    def evaluation_view(run_id: str) -> Dict[str, Any]:
        try:
            return EVALUATIONS.evaluation_view(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/evaluations/{run_id}/evidence")
    def list_evidence(run_id: str) -> Dict[str, Any]:
        if not STORE.get_run(run_id):
            raise HTTPException(status_code=404, detail="run not found")
        return {"evidence": [item.dict() for item in STORE.list_evidence(run_id)]}

    @app.get("/api/evaluations/{run_id}/scores")
    def list_scores(run_id: str) -> Dict[str, Any]:
        if not STORE.get_run(run_id):
            raise HTTPException(status_code=404, detail="run not found")
        return {"scores": [item.dict() for item in STORE.list_scores(run_id)]}

    @app.get("/api/evaluations/{run_id}/llm-logs")
    def list_llm_logs(run_id: str) -> Dict[str, Any]:
        if not STORE.get_run(run_id):
            raise HTTPException(status_code=404, detail="run not found")
        logs = []
        for item in STORE.list_llm_call_logs(run_id):
            payload = item.dict()
            payload["raw_event_count"] = len(payload.pop("raw_events", []) or [])
            logs.append(payload)
        return {"logs": logs}

    @app.post("/api/evaluations/{run_id}/prd")
    def generate_prd(run_id: str) -> Dict[str, Any]:
        try:
            report = EVALUATIONS.generate_prd(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"report": report.dict()}

    @app.get("/api/reports/{report_id}")
    def get_report(report_id: str) -> Dict[str, Any]:
        report = STORE.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="report not found")
        return {"report": report.dict()}

    @app.get("/api/reports/{report_id}/markdown")
    def get_report_markdown(report_id: str) -> FileResponse:
        report = STORE.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail="report not found")
        path = Path(report.markdown_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="report markdown not found")
        media_type = "text/markdown" if report.report_type == ReportType.EVALUATION else "text/plain"
        return FileResponse(path, media_type=media_type, filename=path.name)

    @app.get("/api/evaluations/{run_id}/stream")
    async def stream_events(run_id: str) -> StreamingResponse:
        if not STORE.get_run(run_id):
            raise HTTPException(status_code=404, detail="run not found")

        async def event_generator():
            seen = set()
            while True:
                events = STORE.list_events(run_id)
                for event in events:
                    if event.id in seen:
                        continue
                    seen.add(event.id)
                    payload = event.dict()
                    yield f"event: {event.event_type}\ndata: {json.dumps(payload, default=str)}\n\n"
                run = STORE.get_run(run_id)
                if run and run.status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}:
                    break
                await asyncio.sleep(0.5)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return app


app = create_app()
