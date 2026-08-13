import { LoaderCircle } from "lucide-react";

export function LoadingState({
  label = "Cargando información",
}: {
  label?: string;
}): React.JSX.Element {
  return (
    <output className="loading-state">
      <LoaderCircle size={22} aria-hidden="true" />
      <span>{label}</span>
    </output>
  );
}
