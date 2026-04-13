import type { CSSProperties } from "react";

interface ScoreDonutProps {
  score?: number | null;
  label: string;
}

export function ScoreDonut({ score, label }: ScoreDonutProps) {
  const safeScore = typeof score === "number" ? Math.max(0, Math.min(score, 100)) : 0;
  const style = {
    "--score": `${safeScore * 3.6}deg`,
  } as CSSProperties;

  return (
    <div className="score-donut" style={style} aria-label={`${label}: ${safeScore}`}>
      <div>
        <strong>{typeof score === "number" ? score.toFixed(0) : "-"}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}
