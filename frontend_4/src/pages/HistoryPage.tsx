import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import { ArrowRight, CalendarDays, FileText, Info } from "lucide-react";
import { useAuth } from "../app/AuthContext";
import { api } from "../app/api";
import { HistoryChart, type HistoryMetric, historyMetricGroups } from "../components/HistoryChart";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { PrivateFeatureGate } from "../components/PrivateFeatureGate";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";

function latestRange(
  history: Parameters<typeof HistoryChart>[0]["analyses"],
  metric: HistoryMetric,
): string {
  const latestValue = [...history]
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
    .flatMap((analysis) => analysis.lab_values)
    .find((value) => value.name === metric.key);
  return latestValue
    ? `${latestValue.ref_min}–${latestValue.ref_max} ${metric.unit}`
    : "Sin rango disponible";
}

export function HistoryPage(): React.JSX.Element {
  const { user } = useAuth();
  const { petId } = useParams({ strict: false }) as { petId: string };
  const {
    data: pet,
    isLoading: petLoading,
    error: petError,
    refetch: refetchPet,
  } = useQuery({ queryKey: ["pet", petId], queryFn: () => api.pet(petId), enabled: Boolean(user) });
  const {
    data: history = [],
    isLoading: historyLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useQuery({
    queryKey: ["history", petId],
    queryFn: () => api.history({ petId }),
    enabled: Boolean(user),
  });

  if (!user) {
    return (
      <PrivateFeatureGate
        icon={FileText}
        title="Historial personalizado no disponible en modo invitado"
        description="El historial personalizado está disponible cuando inicias sesión y registras una mascota. El análisis invitado no se guarda."
      />
    );
  }

  if (petLoading || historyLoading) return <LoadingState label="Cargando historial" />;
  if (petError || !pet) {
    return (
      <StatePanel
        icon={FileText}
        title="No fue posible abrir esta mascota"
        description="El perfil solicitado no está disponible o no pudo cargarse."
        tone="error"
        action={
          <button
            className="button button--secondary"
            type="button"
            onClick={() => void refetchPet()}
          >
            Reintentar
          </button>
        }
      />
    );
  }
  if (historyError) {
    return (
      <StatePanel
        icon={FileText}
        title="No fue posible cargar el historial"
        description="El perfil está disponible, pero sus hemogramas no pudieron recuperarse."
        tone="error"
        action={
          <button
            className="button button--secondary"
            type="button"
            onClick={() => void refetchHistory()}
          >
            Reintentar
          </button>
        }
      />
    );
  }

  return (
    <div className="history-page page-flow">
      <PageHeader
        eyebrow={`Historial privado · ${pet.name}`}
        title="Hemogramas registrados"
        description="Vista cronológica de datos previos. No realiza una conclusión clínica automática sobre la evolución."
        actions={
          <Link className="button button--secondary" to="/analisis/nuevo">
            Nuevo hemograma
          </Link>
        }
      />

      {history.length === 0 ? (
        <StatePanel
          icon={FileText}
          title="Aún no hay hemogramas"
          description={`Carga el primer hemograma de ${pet.name} para comenzar su historial.`}
          action={
            <Link className="button button--primary" to="/analisis/nuevo">
              Nuevo hemograma
            </Link>
          }
        />
      ) : (
        <>
          <section className="history-note">
            <Info size={19} aria-hidden="true" />
            <p>
              Las líneas ayudan a localizar cambios numéricos. No significan por sí solas mejoría,
              empeoramiento ni respuesta a tratamiento.
            </p>
          </section>

          <section className="history-visualization" aria-labelledby="history-visualization-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Visualización</p>
                <h2 id="history-visualization-title">Valores principales en el tiempo</h2>
              </div>
              <span>{history.length} registros</span>
            </div>
            {historyMetricGroups.map((group) => (
              <section className="history-chart-group" key={group.title}>
                <div className="history-chart-group__heading">
                  <div>
                    <h3>{group.title}</h3>
                    <p>{group.description}</p>
                  </div>
                </div>
                <div className="history-chart-grid">
                  {group.metrics.map((metric) => (
                    <article className="dashboard-panel history-metric-card" key={metric.key}>
                      <div className="history-metric-card__heading">
                        <div>
                          <h3>{metric.label}</h3>
                          <span>
                            {metric.key} · {metric.unit}
                          </span>
                        </div>
                        <small>Rango: {latestRange(history, metric)}</small>
                      </div>
                      <HistoryChart analyses={history} metric={metric} />
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </section>

          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Cronología</p>
                <h2>Resultados individuales</h2>
              </div>
              <CalendarDays size={20} aria-hidden="true" />
            </div>
            <div className="history-list">
              {history.map((analysis) => (
                <article key={analysis.id}>
                  <div className="history-list__date">
                    <strong>
                      {new Intl.DateTimeFormat("es-DO", { day: "2-digit", month: "short" }).format(
                        new Date(analysis.created_at),
                      )}
                    </strong>
                    <span>{new Date(analysis.created_at).getFullYear()}</span>
                  </div>
                  <div>
                    <h3>{analysis.diagnoses[0]}</h3>
                    <p>{analysis.summary}</p>
                    <div className="history-values">
                      {analysis.lab_values
                        .filter((value) => ["WBC", "HCT", "PLT"].includes(value.name))
                        .map((value) => (
                          <span key={value.name}>
                            {value.name} <strong>{value.value}</strong>
                          </span>
                        ))}
                    </div>
                  </div>
                  <StatusBadge tone={analysis.findings[0]?.severity ?? "success"}>
                    {analysis.status === "success" ? "Completo" : "Con revisión"}
                  </StatusBadge>
                  <Link
                    className="icon-button"
                    to="/analisis/$analysisId"
                    params={{ analysisId: analysis.id }}
                    aria-label={`Abrir análisis del ${analysis.created_at}`}
                  >
                    <ArrowRight size={17} />
                  </Link>
                </article>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
