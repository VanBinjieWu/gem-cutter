import { StatusBadge } from "./StatusBadge";
import type { EvaluationEvent, EvaluationRun } from "../../types/api";

const stageLabels = [
  "planning",
  "collecting_signals",
  "normalizing_evidence",
  "clustering_evidence",
  "scoring",
  "gate_review",
  "rendering",
  "completed",
];

interface RunTimelineProps {
  run?: EvaluationRun;
  events: EvaluationEvent[];
}

export function RunTimeline({ run, events }: RunTimelineProps) {
  if (!run) {
    return (
      <div className="empty-state compact">
        <strong>暂无运行</strong>
        <p>启动评估后，这里会显示阶段、进度和实时事件。</p>
      </div>
    );
  }

  return (
    <div className="run-timeline">
      <div className="run-progress">
        <div>
          <strong>{run.progress}%</strong>
          <span>{run.message}</span>
        </div>
        <StatusBadge value={run.status} />
      </div>

      <div className="stage-rail">
        {stageLabels.map((stage) => (
          <div className={run.stage === stage ? "stage-rail__item is-active" : "stage-rail__item"} key={stage}>
            <span />
            <strong>{stage}</strong>
          </div>
        ))}
      </div>

      <div className="event-feed">
        <header>
          <strong>实时事件</strong>
          <small>{events.length} events</small>
        </header>
        {events.length ? (
          events.slice(-12).map((event) => (
            <article key={event.id}>
              <StatusBadge value={event.event_type} tone="info" />
              <pre>{JSON.stringify(event.payload, null, 2)}</pre>
            </article>
          ))
        ) : (
          <p>等待后端 SSE 事件。</p>
        )}
      </div>
    </div>
  );
}

