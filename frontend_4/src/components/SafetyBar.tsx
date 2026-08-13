import { Link } from "@tanstack/react-router";
import { ShieldCheck } from "lucide-react";

export function SafetyBar(): React.JSX.Element {
  return (
    <div className="safety-bar" role="note">
      <ShieldCheck size={16} aria-hidden="true" />
      <span>
        HemoVet ofrece orientación educativa sobre hemogramas caninos. No reemplaza el juicio ni la
        evaluación de un médico veterinario.
      </span>
      <Link to="/limites">Ver límites</Link>
    </div>
  );
}
