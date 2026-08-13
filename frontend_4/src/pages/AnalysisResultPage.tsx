import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  Bot,
  CheckCircle2,
  ClipboardPlus,
  Copy,
  FileText,
} from "lucide-react";
import { api } from "../app/api";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-DO", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

export function AnalysisResultPage(): React.JSX.Element {
  const { analysisId } = useParams({ strict: false }) as { analysisId: string };
  const { data, isLoading, error } = useQuery({
    queryKey: ["analysis", analysisId],
    queryFn: () => api.analysis(analysisId),
  });

  if (isLoading) return <LoadingState label="Cargando resultado" />;
  if (error || !data) {
    return <div className="form-error">No fue posible abrir el análisis solicitado.</div>;
  }

  return (
    <div className="result-page page-flow">
      <PageHeader
        eyebrow={`${data.pet_name ?? "Mascota no asociada"} · ${formatDate(data.created_at)}`}
        title="Resultado orientativo"
        description="Lectura estructurada del hemograma confirmado. No constituye un diagnóstico."
        actions={
          <Link className="button button--secondary" to="/analisis/nuevo">
            <ClipboardPlus size={17} aria-hidden="true" /> Nuevo hemograma
          </Link>
        }
      />

      <div className="result-layout">
        <div className="result-main">
          <section className="result-summary">
            <div className="result-summary__status">
              <span className="result-summary__icon">
                <FileText size={24} aria-hidden="true" />
              </span>
              <div>
                <p className="eyebrow">Síntesis</p>
                <h2>{data.diagnoses[0]}</h2>
              </div>
              <StatusBadge tone={data.findings[0]?.severity ?? "info"}>
                Requiere contexto
              </StatusBadge>
            </div>
            <p>{data.summary}</p>
            <div className="result-summary__metrics">
              <div>
                <span>Calidad</span>
                <strong>{Math.round(data.quality_score * 100)}%</strong>
              </div>
              <div>
                <span>Estado</span>
                <strong>{data.status === "success" ? "Completo" : "Con revisión"}</strong>
              </div>
            </div>
          </section>

          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Hallazgos</p>
                <h2>Qué observó el sistema</h2>
              </div>
            </div>
            <div className="findings-list">
              {data.findings.map((finding) => (
                <article key={finding.label} data-severity={finding.severity}>
                  <span className="finding-marker" aria-hidden="true" />
                  <div>
                    <div className="finding-title">
                      <h3>{finding.label}</h3>
                      <StatusBadge tone={finding.severity}>
                        {finding.severity === "danger"
                          ? "Prioridad"
                          : finding.severity === "warn"
                            ? "Atención"
                            : "Informativo"}
                      </StatusBadge>
                    </div>
                    <p>{finding.detail}</p>
                    {finding.glossary_slug && (
                      <Link
                        to="/biblioteca/$slug"
                        params={{ slug: finding.glossary_slug }}
                        className="text-link"
                      >
                        Consultar definición <ArrowRight size={15} />
                      </Link>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Valores confirmados</p>
                <h2>Datos principales del CBC</h2>
              </div>
            </div>
            <section
              className="table-wrap"
              aria-label="Valores confirmados del hemograma"
              // biome-ignore lint/a11y/noNoninteractiveTabindex: Scrollable table regions must be keyboard focusable.
              tabIndex={0}
            >
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Parámetro</th>
                    <th>Resultado</th>
                    <th>Referencia</th>
                    <th>Lectura</th>
                  </tr>
                </thead>
                <tbody>
                  {data.lab_values.map((value) => (
                    <tr key={value.name}>
                      <th scope="row">
                        {value.label}
                        <span>{value.name}</span>
                      </th>
                      <td className="numeric">
                        {value.value} <span>{value.unit}</span>
                      </td>
                      <td>
                        {value.ref_min}–{value.ref_max}
                      </td>
                      <td>
                        <StatusBadge tone={value.status}>
                          {value.status === "normal"
                            ? "En rango"
                            : value.status === "low"
                              ? "Bajo"
                              : value.status === "high"
                                ? "Alto"
                                : "Crítico"}
                        </StatusBadge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </section>
        </div>

        <aside className="result-aside">
          {data.qc_flags.length > 0 && (
            <section className="quality-panel">
              <AlertTriangle size={20} aria-hidden="true" />
              <div>
                <p className="eyebrow">Calidad de muestra</p>
                <h2>Revisión recomendada</h2>
                {data.qc_flags.map((flag) => (
                  <p key={flag}>{flag}</p>
                ))}
              </div>
            </section>
          )}
          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Siguiente paso</p>
                <h2>Usar este resultado</h2>
              </div>
            </div>
            <div className="action-stack">
              <a
                href={
                  `/asistente?scope=selected_hemogram&analysis_id=${encodeURIComponent(data.id)}` +
                  (data.pet_id ? `&pet_id=${encodeURIComponent(data.pet_id)}` : "")
                }
                className="button button--primary button--full"
              >
                <Bot size={18} aria-hidden="true" /> Preguntar al asistente
              </a>
              <button
                className="button button--secondary button--full"
                type="button"
                onClick={() => navigator.clipboard.writeText(data.summary)}
              >
                <Copy size={17} aria-hidden="true" /> Copiar resumen
              </button>
              <Link to="/biblioteca" className="button button--ghost button--full">
                <BookOpen size={17} aria-hidden="true" /> Abrir biblioteca
              </Link>
            </div>
          </section>
          <section className="clinical-reminder clinical-reminder--strong">
            <CheckCircle2 size={20} aria-hidden="true" />
            <div>
              <strong>Consulta veterinaria</strong>
              <p>El resultado debe relacionarse con signos, examen físico y otras pruebas.</p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
