import clsx from "clsx";

interface StatusBadgeProps {
  value?: string | null;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
}

function inferTone(value?: string | null): NonNullable<StatusBadgeProps["tone"]> {
  if (!value) return "neutral";
  if (["completed", "go", "valid", "configured"].includes(value)) return "success";
  if (["conditional_go", "hold", "running", "evaluating"].includes(value)) return "warning";
  if (["failed", "stop", "invalid", "cancelled"].includes(value)) return "danger";
  if (["planning", "collecting_signals", "scoring", "rendering"].includes(value)) return "info";
  return "neutral";
}

export function StatusBadge({ value, tone }: StatusBadgeProps) {
  const label = value || "unknown";

  return <span className={clsx("status-badge", `status-badge--${tone || inferTone(value)}`)}>{label}</span>;
}

