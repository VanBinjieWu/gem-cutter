import { StatusBadge } from "./StatusBadge";
import type { EvidenceItem } from "../../types/api";

interface EvidenceBoardProps {
  evidence: EvidenceItem[];
  selectedDimension: string;
  selectedEvidenceId: string;
  onSelectEvidence: (evidenceId: string) => void;
}

export function EvidenceBoard({
  evidence,
  selectedDimension,
  selectedEvidenceId,
  onSelectEvidence,
}: EvidenceBoardProps) {
  const filteredEvidence = selectedDimension
    ? evidence.filter((item) => item.dimension === selectedDimension)
    : evidence;
  const selectedEvidence = evidence.find((item) => item.id === selectedEvidenceId) || filteredEvidence[0];

  return (
    <div className="evidence-workbench">
      <div className="evidence-list">
        <header>
          <strong>{selectedDimension || "全部维度"}</strong>
          <small>{filteredEvidence.length} evidence items</small>
        </header>
        {filteredEvidence.length ? (
          filteredEvidence.map((item) => (
            <button
              className={selectedEvidence?.id === item.id ? "evidence-item is-active" : "evidence-item"}
              key={item.id}
              onClick={() => onSelectEvidence(item.id)}
            >
              <div>
                <StatusBadge value={item.status} />
                <StatusBadge value={item.dimension} tone="info" />
              </div>
              <strong>{item.title}</strong>
              <p>{item.summary}</p>
              <span>
                credibility {item.credibility_score} · hotness {item.hotness_score} · {item.source_platform}
              </span>
            </button>
          ))
        ) : (
          <div className="empty-state compact">
            <strong>暂无证据</strong>
            <p>该维度还没有可展示的 EvidenceItem。</p>
          </div>
        )}
      </div>

      <aside className="evidence-inspector">
        {selectedEvidence ? (
          <>
            <div className="inspector-header">
              <StatusBadge value={selectedEvidence.dimension} tone="info" />
              <StatusBadge value={selectedEvidence.source_type} tone="neutral" />
            </div>
            <h3>{selectedEvidence.title}</h3>
            <p>{selectedEvidence.summary}</p>
            <dl>
              <div>
                <dt>ID</dt>
                <dd>{selectedEvidence.id}</dd>
              </div>
              <div>
                <dt>Credibility</dt>
                <dd>{selectedEvidence.credibility_score}</dd>
              </div>
              <div>
                <dt>Relevance</dt>
                <dd>{selectedEvidence.relevance_score}</dd>
              </div>
              <div>
                <dt>Freshness</dt>
                <dd>{selectedEvidence.freshness_score}</dd>
              </div>
              <div>
                <dt>Sentiment</dt>
                <dd>{selectedEvidence.sentiment_label}</dd>
              </div>
              <div>
                <dt>Published</dt>
                <dd>{selectedEvidence.published_at || "unknown"}</dd>
              </div>
            </dl>
            {selectedEvidence.url ? (
              <a className="button-ghost" href={selectedEvidence.url} target="_blank" rel="noreferrer">
                打开来源
              </a>
            ) : null}
            <pre>{selectedEvidence.content}</pre>
          </>
        ) : (
          <div className="empty-state compact">
            <strong>选择证据</strong>
            <p>点击左侧证据查看来源、可信度和正文片段。</p>
          </div>
        )}
      </aside>
    </div>
  );
}

