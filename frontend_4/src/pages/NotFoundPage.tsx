import { Link } from "@tanstack/react-router";
import { ArrowLeft, SearchX } from "lucide-react";
import { StatePanel } from "../components/StatePanel";

export function NotFoundPage(): React.JSX.Element {
  return (
    <StatePanel
      icon={SearchX}
      title="Página no encontrada"
      description="La dirección solicitada no existe o ya no está disponible."
      action={
        <Link className="button button--primary" to="/panel">
          <ArrowLeft size={17} aria-hidden="true" /> Volver al resumen
        </Link>
      }
    />
  );
}
