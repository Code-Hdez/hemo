import type { LabStatus, Severity } from "../domain/types";

interface StatusBadgeProps {
  tone: Severity | LabStatus | "neutral" | "success";
  children: React.ReactNode;
}

export function StatusBadge({ tone, children }: StatusBadgeProps): React.JSX.Element {
  return (
    <span className="status-badge" data-tone={tone}>
      {children}
    </span>
  );
}
