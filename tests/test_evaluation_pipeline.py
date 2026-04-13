import tempfile
import unittest
from pathlib import Path

from backend.app.domain.models import GateAction, RunStatus
from backend.app.domain.services import EvaluationService, ProjectService
from backend.app.domain.store import JsonStore


class EvaluationPipelineTest(unittest.TestCase):
    def test_evaluation_pipeline_creates_ledgers_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = JsonStore(root / "store.json")
            projects = ProjectService(store)
            evaluations = EvaluationService(store, artifact_dir=root / "reports")

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
            self.assertTrue(Path(reports[0].markdown_path).exists())

            view = evaluations.evaluation_view(run.id)
            self.assertIn("evidence_summary", view)
            self.assertIn("score_summary", view)


if __name__ == "__main__":
    unittest.main()
