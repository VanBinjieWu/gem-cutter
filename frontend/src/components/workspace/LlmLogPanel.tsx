import { StatusBadge } from "./StatusBadge";
import type { LlmCallLog } from "../../types/api";

interface LlmLogPanelProps {
  logs: LlmCallLog[];
}

export function LlmLogPanel({ logs }: LlmLogPanelProps) {
  if (!logs.length) {
    return (
      <div className="empty-state compact">
        <strong>暂无模型日志</strong>
        <p>Ark 搜索或 PRD 生成时，会在这里展示模型调用记录。</p>
      </div>
    );
  }

  return (
    <div className="llm-log-list">
      {logs.map((log) => (
        <article className="llm-log-card" key={log.id}>
          <header>
            <div>
              <StatusBadge value={log.status} />
              <StatusBadge value={log.purpose} tone="info" />
              {log.dimension ? <StatusBadge value={log.dimension} tone="neutral" /> : null}
            </div>
            <small>{log.event_count} events</small>
          </header>
          <strong>{log.model}</strong>
          {log.query ? <p>{log.query}</p> : null}
          <div className="llm-log-columns">
            <pre>{log.reasoning_text || "暂无思考摘要"}</pre>
            <pre>{log.output_text || log.error || "暂无输出文本"}</pre>
          </div>
        </article>
      ))}
    </div>
  );
}

