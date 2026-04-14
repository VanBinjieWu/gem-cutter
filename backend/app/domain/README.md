# Gem Cutter MVP Backend Slice

This package implements the first MVP vertical slice:

1. Create an `OpportunityProject`.
2. Start an `EvaluationRun`.
3. Collect mock `RawSignal` items through Source Adapters.
4. Normalize them into `EvidenceItem` records.
5. Cluster evidence into `EvidenceCluster` records.
6. Produce `ScoreLedger` records.
7. Decide a `GateDecision`.
8. Render an evaluation report and, when allowed, a PRD report.

The current storage backend is SQLite under `data/gem_cutter.db` so the app can run locally without Postgres. The service boundaries mirror the intended repository-backed architecture and can be swapped later. Legacy `data/gem_cutter_store.json` content is imported into SQLite on startup when the database is empty.
