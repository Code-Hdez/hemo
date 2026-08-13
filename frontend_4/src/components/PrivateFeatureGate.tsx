import { Link } from "@tanstack/react-router";
import type { LucideIcon } from "lucide-react";
import { LockKeyhole } from "lucide-react";
import { StatePanel } from "./StatePanel";

interface PrivateFeatureGateProps {
  icon?: LucideIcon;
  title?: string;
  description: string;
}

export function PrivateFeatureGate({
  icon = LockKeyhole,
  title = "Esta función requiere iniciar sesión",
  description,
}: PrivateFeatureGateProps): React.JSX.Element {
  return (
    <StatePanel
      icon={icon}
      title={title}
      description={description}
      action={
        <div className="panel-actions">
          <Link className="button button--primary" to="/">
            Iniciar sesión
          </Link>
          <Link className="button button--secondary" to="/registro">
            Crear cuenta
          </Link>
        </div>
      }
    />
  );
}
