import type { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  kicker?: string;
  action?: ReactNode;
  children: ReactNode;
}

export function SectionCard({ title, kicker, action, children }: SectionCardProps) {
  return (
    <section className="section-card">
      <header className="section-card__header">
        <div>
          {kicker ? <p>{kicker}</p> : null}
          <h2>{title}</h2>
        </div>
        {action ? <div className="section-card__action">{action}</div> : null}
      </header>
      {children}
    </section>
  );
}

