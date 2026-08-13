import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

interface StatePanelProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
  tone?: "empty" | "error";
}

export function StatePanel({
  icon: Icon,
  title,
  description,
  action,
  tone = "empty",
}: StatePanelProps): React.JSX.Element {
  return (
    <section className="state-panel" data-tone={tone} role={tone === "error" ? "alert" : "status"}>
      <span className="state-panel__icon">
        <Icon size={24} aria-hidden="true" />
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <div className="state-panel__action">{action}</div>}
    </section>
  );
}
