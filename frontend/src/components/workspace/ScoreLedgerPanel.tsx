import { ScoreDonut } from "../charts/ScoreDonut";
import { StatusBadge } from "./StatusBadge";
import type { GateDecision, ScoreLedger } from "../../types/api";

interface ScoreLedgerPanelProps {
  gate?: GateDecision | null;
  scores: ScoreLedger[];
  selectedDimension: string;
  onSelectDimension: (dimension: string) => void;
}

export function ScoreLedgerPanel({ gate, scores, selectedDimension, onSelectDimension }: ScoreLedgerPanelProps) {
  return (
    <div className="score-workbench">
      <ScoreDonut score={gate?.total_score} label="Total" />
      <div className="score-ledger-list">
        {scores.length ? (
          scores.map((score) => (
            <button
              className={selectedDimension === score.dimension ? "score-ledger-item is-active" : "score-ledger-item"}
              key={score.id}
              onClick={() => onSelectDimension(selectedDimension === score.dimension ? "" : score.dimension)}
            >
              <div>
                <strong>{score.dimension}</strong>
                <small>{score.rationale}</small>
                <span>
                  {score.positive_evidence_ids.length} refs · weight {(score.weight * 100).toFixed(0)}%
                </span>
              </div>
              <div>
                <b>{score.score.toFixed(0)}</b>
                <StatusBadge value={`conf ${score.confidence}`} tone="neutral" />
              </div>
            </button>
          ))
        ) : (
          <div className="empty-state compact">
            <strong>等待评分</strong>
            <p>评分阶段完成后，会展示 7 个 ScoreLedger 维度。</p>
          </div>
        )}
      </div>
    </div>
  );
}

