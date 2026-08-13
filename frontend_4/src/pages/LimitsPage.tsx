import {
  AlertTriangle,
  CheckCircle2,
  Database,
  MessageSquareWarning,
  ShieldCheck,
} from "lucide-react";
import { PageHeader } from "../components/PageHeader";

const limits = [
  {
    icon: Database,
    title: "Solo hemograma canino",
    text: "No aplica a otras especies ni procesa bioquímica, radiografías o imágenes de frotis.",
  },
  {
    icon: MessageSquareWarning,
    title: "Sin diagnóstico ni tratamiento",
    text: "Los patrones son probabilísticos. El asistente no receta, no indica dosis y no confirma enfermedades.",
  },
  {
    icon: AlertTriangle,
    title: "Depende de la calidad del dato",
    text: "Errores de extracción, calibración o artefactos de muestra pueden afectar la clasificación.",
  },
  {
    icon: Database,
    title: "Extracción asistida por IA",
    text: "La lectura del archivo puede usar OpenRouter, Google Gemini y extracción local con OCR como métodos técnicos de apoyo.",
  },
  {
    icon: ShieldCheck,
    title: "Vigilancia agregada",
    text: "El mapa muestra señales de los registros disponibles, no prevalencia real ni ubicaciones exactas.",
  },
];

export function LimitsPage(): React.JSX.Element {
  return (
    <div className="limits-page page-flow">
      <PageHeader
        eyebrow="Uso responsable"
        title="Alcance y límites de HemoVet"
        description="Condiciones que deben acompañar cualquier lectura generada por la plataforma."
      />
      <div className="limits-grid">
        {limits.map((item) => (
          <article key={item.title}>
            <span>
              <item.icon size={22} aria-hidden="true" />
            </span>
            <h2>{item.title}</h2>
            <p>{item.text}</p>
          </article>
        ))}
      </div>
      <section className="responsible-use">
        <CheckCircle2 size={24} aria-hidden="true" />
        <div>
          <p className="eyebrow">Uso previsto</p>
          <h2>Preparar una conversación mejor informada</h2>
          <p>
            HemoVet organiza valores y explica términos para propietarios. Las decisiones clínicas
            corresponden al veterinario que conoce la historia, examina al paciente y determina las
            pruebas necesarias.
          </p>
        </div>
      </section>
    </div>
  );
}
