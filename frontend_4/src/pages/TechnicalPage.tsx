import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, Database, ShieldCheck } from "lucide-react";
import { useAuth } from "../app/AuthContext";
import { api } from "../app/api";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { PrivateFeatureGate } from "../components/PrivateFeatureGate";
import { StatusBadge } from "../components/StatusBadge";

export function TechnicalPage(): React.JSX.Element {
  const { user } = useAuth();
  const { data, isLoading, error } = useQuery({
    queryKey: ["model-quality"],
    queryFn: api.modelQuality,
    enabled: user?.role === "admin",
  });
  const { data: activation } = useQuery({
    queryKey: ["label-activation"],
    queryFn: api.labelActivation,
    enabled: user?.role === "admin",
  });
  const { data: breeds } = useQuery({
    queryKey: ["breed-distribution", 30],
    queryFn: () => api.breedDistribution(30),
    enabled: user?.role === "admin",
  });

  if (!user) {
    return (
      <PrivateFeatureGate description="El panel técnico requiere iniciar sesión con una cuenta autorizada." />
    );
  }
  if (user.role !== "admin") {
    return <div className="form-error">No tienes permiso para ver el panel técnico.</div>;
  }
  if (isLoading) return <LoadingState label="Cargando métricas técnicas" />;
  if (error || !data) return <div className="form-error">No fue posible cargar las métricas.</div>;

  return (
    <div className="technical-page page-flow">
      <PageHeader
        eyebrow="Acceso administrativo"
        title="Panel técnico del modelo"
        description="Métricas metodológicas separadas de la experiencia ciudadana."
      />
      <section className="metric-grid technical-metrics">
        <article className="metric-card">
          <span className="metric-card__icon">
            <Activity size={19} aria-hidden="true" />
          </span>
          <div>
            <p>PR-AUC macro</p>
            <strong>{Math.round(data.prauc_macro * 100)}%</strong>
            <small>Versión {data.version}</small>
          </div>
        </article>
        <article className="metric-card">
          <span className="metric-card__icon" data-tone="success">
            <Database size={19} aria-hidden="true" />
          </span>
          <div>
            <p>Validación externa</p>
            <strong>{data.external_validation.n}</strong>
            <small>{data.external_validation.dataset}</small>
          </div>
        </article>
        <article className="metric-card">
          <span className="metric-card__icon" data-tone="success">
            <ShieldCheck size={19} aria-hidden="true" />
          </span>
          <div>
            <p>Gates aprobados</p>
            <strong>{Object.values(data.gates).filter((gate) => gate === "pass").length}</strong>
            <small>Controles operativos visibles</small>
          </div>
        </article>
      </section>

      <section className="dashboard-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Rendimiento por etiqueta</p>
            <h2>Métricas oficiales</h2>
          </div>
        </div>
        <div className="technical-labels">
          {data.labels.map((label) => (
            <article key={label.name}>
              <div>
                <strong>{label.name}</strong>
                <StatusBadge tone="success">Oficial</StatusBadge>
              </div>
              <div className="metric-bars">
                <span>
                  <span>PR-AUC</span>
                  <i style={{ width: `${label.pr_auc * 100}%` }} />
                  <strong>{Math.round(label.pr_auc * 100)}%</strong>
                </span>
                <span>
                  <span>F1</span>
                  <i style={{ width: `${label.f1 * 100}%` }} />
                  <strong>{Math.round(label.f1 * 100)}%</strong>
                </span>
              </div>
            </article>
          ))}
        </div>
      </section>

      {activation && (
        <section className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Comparación de cohortes</p>
              <h2>Activación por etiqueta</h2>
            </div>
          </div>
          <div className="technical-labels">
            {activation.labels.map((label) => (
              <article key={label.name}>
                <div>
                  <strong>{label.name}</strong>
                  <StatusBadge tone="neutral">IDEXX / DAP</StatusBadge>
                </div>
                <div className="metric-bars">
                  <span>
                    <span>IDEXX</span>
                    <i style={{ width: `${label.rate_idexx * 100}%` }} />
                    <strong>{Math.round(label.rate_idexx * 100)}%</strong>
                  </span>
                  <span>
                    <span>DAP</span>
                    <i style={{ width: `${label.rate_dap * 100}%` }} />
                    <strong>{Math.round(label.rate_dap * 100)}%</strong>
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {breeds && (
        <section className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Registros actuales</p>
              <h2>Distribución de razas</h2>
            </div>
            <span>{breeds.total} mascotas</span>
          </div>
          {breeds.breeds.length === 0 ? (
            <div className="empty-inline">Aún no hay razas registradas para mostrar.</div>
          ) : (
            <div className="gate-list">
              {breeds.breeds.slice(0, 8).map((breed) => (
                <div key={breed.name}>
                  <Database size={18} aria-hidden="true" />
                  <span>{breed.name}</span>
                  <StatusBadge tone="neutral">
                    {breed.count} · {breed.pct}%
                  </StatusBadge>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="dashboard-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Controles</p>
            <h2>Gates operativos</h2>
          </div>
        </div>
        <div className="gate-list">
          {Object.entries(data.gates).map(([name, status]) => (
            <div key={name}>
              <CheckCircle2 size={18} aria-hidden="true" />
              <span>{name.replaceAll("_", " ")}</span>
              <StatusBadge tone={status === "pass" ? "success" : "warn"}>{status}</StatusBadge>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
