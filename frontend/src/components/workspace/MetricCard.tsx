import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: ReactNode;
  helper?: string;
  accent?: "teal" | "amber" | "red" | "ink";
}

export function MetricCard({ label, value, helper, accent = "teal" }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${accent}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {helper ? <small>{helper}</small> : null}
    </article>
  );
}

