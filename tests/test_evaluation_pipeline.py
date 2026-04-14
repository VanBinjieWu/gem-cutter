import tempfile
import unittest
from pathlib import Path

from backend.app.core.config import AppSettings
from backend.app.domain.models import GateAction, RunStatus
from backend.app.domain.services import EvaluationService, ProjectService
from backend.app.domain.store import SQLiteStore


class EvaluationPipelineTest(unittest.TestCase):
    def test_evaluation_pipeline_creates_ledgers_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = SQLiteStore(root / "store.db")
            projects = ProjectService(store)
            settings = AppSettings.parse_obj({"llm": {"provider": "mock"}, "search": {"provider": "mock"}})
            evaluations = EvaluationService(store, artifact_dir=root / "reports", settings=settings)

            project = projects.create_project(
                title="AI Video Script Tool",
                input_topic="AI video script generation tool for creators",
                target_market="China creators",
                target_user_hint="short video creators",
            )
            run = evaluations.start_run(project.id)
            completed = evaluations.run(run.id)

            self.assertEqual(completed.status, RunStatus.COMPLETED)
            self.assertGreaterEqual(len(store.list_raw_signals(run.id)), 7)
            self.assertGreaterEqual(len(store.list_evidence(run.id)), 7)
            self.assertEqual(len(store.list_scores(run.id)), 7)

            gate = store.get_latest_gate_decision(run.id)
            self.assertIsNotNone(gate)
            self.assertIn(gate.action, {item.value for item in GateAction})

            reports = store.list_reports(run.id)
            self.assertTrue(reports)
            self.assertTrue(reports[0].markdown_path.startswith("sqlite://"))
            self.assertIn("# Evaluation Report", store.get_report_markdown(reports[0].id))

            view = evaluations.evaluation_view(run.id)
            self.assertIn("evidence_summary", view)
            self.assertIn("score_summary", view)

            reloaded = SQLiteStore(root / "store.db")
            self.assertIsNotNone(reloaded.get_project(project.id))
            self.assertEqual(len(reloaded.list_scores(run.id)), 7)
            self.assertIn("# Evaluation Report", reloaded.get_report_markdown(reports[0].id))


if __name__ == "__main__":
    unittest.main()
