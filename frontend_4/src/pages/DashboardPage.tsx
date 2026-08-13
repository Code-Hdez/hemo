import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  BookOpen,
  Bot,
  CalendarDays,
  CheckCircle2,
  ClipboardPlus,
  Clock3,
  FileText,
  Map as MapIcon,
  PawPrint,
  Share2,
} from "lucide-react";
import { useAuth } from "../app/AuthContext";
import { api } from "../app/api";
import { useActivePet } from "../app/PetContext";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { PetAvatar } from "../components/PetAvatar";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("es-DO", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function LimitedDashboard({ guest }: { guest: boolean }): React.JSX.Element {
  return (
    <div className="dashboard-page page-flow">
      <PageHeader
        eyebrow={guest ? "Modo invitado" : "Cuenta sin mascota registrada"}
        title={
          guest ? "Analiza un hemograma sin crear cuenta" : "Puedes analizar sin asociar mascota"
        }
        description={
          guest
            ? "Puedes subir un hemograma, revisar los valores extraídos y ver el resultado del modelo. Tus datos no se guardarán."
            : "Puedes analizar este hemograma sin asociarlo a una mascota. Para guardar historial personalizado, registra una mascota."
        }
        actions={
          <Link className="button button--primary" to="/analisis/nuevo">
            <ClipboardPlus size={18} aria-hidden="true" />
            Nuevo hemograma
          </Link>
        }
      />
      <section className="metric-grid" aria-label="Funciones disponibles" data-tour="panel-kpi">
        <article className="metric-card">
          <span className="metric-card__icon">
            <ClipboardPlus size={19} aria-hidden="true" />
          </span>
          <div>
            <p>Análisis puntual</p>
            <strong>Disponible</strong>
            <small>Extracción, revisión y ML para este hemograma.</small>
          </div>
        </article>
        <article className="metric-card">
          <span className="metric-card__icon" data-tone="attention">
            <CalendarDays size={19} aria-hidden="true" />
          </span>
          <div>
            <p>Historial personalizado</p>
            <strong>Bloqueado</strong>
            <small>
              {guest
                ? "Requiere iniciar sesión y registrar mascota."
                : "Registra una mascota para guardar evolución."}
            </small>
          </div>
        </article>
        <article className="metric-card">
          <span className="metric-card__icon" data-tone="attention">
            <MapIcon size={19} aria-hidden="true" />
          </span>
          <div>
            <p>Mapa y Chat LLM</p>
            <strong>Requieren cuenta</strong>
            <small>Disponibles solo con sesión iniciada.</small>
          </div>
        </article>
      </section>
      <section className="dashboard-panel latest-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Siguiente acción</p>
            <h2>Subir o ingresar valores del hemograma</h2>
          </div>
        </div>
        <p className="latest-panel__summary">
          El resultado temporal se mostrará en esta sesión. Si no hay mascota asociada, no se crea
          historial.
        </p>
        <div className="panel-actions">
          <Link className="button button--primary" to="/analisis/nuevo">
            Nuevo hemograma <ArrowRight size={17} aria-hidden="true" />
          </Link>
          {!guest && (
            <Link className="button button--secondary" to="/mascotas">
              Registrar mascota
            </Link>
          )}
        </div>
      </section>
    </div>
  );
}

export function DashboardPage(): React.JSX.Element {
  const { user } = useAuth();
  const {
    activePet,
    activePetId,
    loading,
    error: petsError,
    refetch: refetchPets,
  } = useActivePet();
  const {
    data: history = [],
    isLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useQuery({
    queryKey: ["history", activePetId],
    queryFn: () => api.history({ petId: activePetId }),
    enabled: Boolean(user && activePetId),
  });
  const latest = history[0];

  if (!user) return <LimitedDashboard guest />;
  if (loading || isLoading) return <LoadingState label="Preparando el resumen" />;
  if (petsError) {
    return (
      <StatePanel
        icon={PawPrint}
        title="No fue posible cargar tus mascotas"
        description="Revisa la conexión e inténtalo nuevamente."
        tone="error"
        action={
          <button
            className="button button--secondary"
            type="button"
            onClick={() => void refetchPets()}
          >
            Reintentar
          </button>
        }
      />
    );
  }
  if (!activePet) {
    return <LimitedDashboard guest={false} />;
  }
  if (historyError) {
    return (
      <StatePanel
        icon={FileText}
        title="No fue posible cargar el resumen"
        description="La mascota está disponible, pero su historial no pudo recuperarse."
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
    <div className="dashboard-page page-flow">
      <PageHeader
        eyebrow={`Mascota activa · ${activePet.name}`}
        title={`Hola, revisemos a ${activePet.name}`}
        description="Un resumen de sus hemogramas guardados y las acciones disponibles."
        actions={
          <Link className="button button--primary" to="/analisis/nuevo">
            <ClipboardPlus size={18} aria-hidden="true" />
            Nuevo hemograma
          </Link>
        }
      />

      <div className="dashboard-layout">
        <div className="dashboard-main">
          <section className="metric-grid" aria-label="Resumen de la mascota" data-tour="panel-kpi">
            <article className="metric-card">
              <span className="metric-card__icon">
                <FileText size={19} aria-hidden="true" />
              </span>
              <div>
                <p>Hemogramas guardados</p>
                <strong>{history.length}</strong>
                <small>Historial privado de {activePet.name}</small>
              </div>
            </article>
            <article className="metric-card">
              <span className="metric-card__icon" data-tone="attention">
                <Clock3 size={19} aria-hidden="true" />
              </span>
              <div>
                <p>Último análisis</p>
                <strong>{latest ? formatDate(latest.created_at) : "Sin datos"}</strong>
                <small>{latest ? "Resultado disponible" : "Carga el primer hemograma"}</small>
              </div>
            </article>
            <article className="metric-card">
              <span className="metric-card__icon" data-tone="success">
                <MapIcon size={19} aria-hidden="true" />
              </span>
              <div>
                <p>Vigilancia comunitaria</p>
                <strong>{activePet.residence_consent ? "Activa" : "Inactiva"}</strong>
                <small>Zona agregada, sin dirección exacta</small>
              </div>
            </article>
          </section>

          <section className="dashboard-panel latest-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Último resultado</p>
                <h2>{latest ? latest.diagnoses[0] : "Aún no hay hemogramas"}</h2>
              </div>
              {latest && (
                <StatusBadge tone={latest.findings[0]?.severity ?? "info"}>Orientativo</StatusBadge>
              )}
            </div>
            {latest ? (
              <>
                <p className="latest-panel__summary">{latest.summary}</p>
                <div className="latest-panel__facts">
                  <div>
                    <span>Calidad de lectura</span>
                    <strong>{Math.round(latest.quality_score * 100)}%</strong>
                  </div>
                  <div>
                    <span>Hallazgos mostrados</span>
                    <strong>{latest.findings.length}</strong>
                  </div>
                </div>
                <div className="panel-actions">
                  <Link
                    className="button button--primary"
                    to="/analisis/$analysisId"
                    params={{ analysisId: latest.id }}
                  >
                    Abrir resultado <ArrowRight size={17} aria-hidden="true" />
                  </Link>
                  <button
                    className="button button--secondary"
                    type="button"
                    onClick={() => navigator.clipboard.writeText(latest.summary)}
                  >
                    <Share2 size={17} aria-hidden="true" /> Copiar resumen
                  </button>
                </div>
              </>
            ) : (
              <div className="empty-inline">
                <p>
                  Carga un archivo o ingresa valores manualmente para comenzar el historial de esta
                  mascota.
                </p>
                <Link className="button button--primary" to="/analisis/nuevo">
                  Nuevo hemograma
                </Link>
              </div>
            )}
          </section>

          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Actividad</p>
                <h2>Hemogramas recientes</h2>
              </div>
              <Link
                className="text-link"
                to="/mascotas/$petId/historial"
                params={{ petId: activePet.id }}
              >
                Ver historial <ArrowRight size={16} />
              </Link>
            </div>
            <div className="activity-list">
              {history.slice(0, 3).map((analysis) => (
                <Link
                  key={analysis.id}
                  className="activity-row"
                  to="/analisis/$analysisId"
                  params={{ analysisId: analysis.id }}
                >
                  <span className="activity-row__icon">
                    <FileText size={18} aria-hidden="true" />
                  </span>
                  <div>
                    <strong>{analysis.diagnoses[0] ?? "Hemograma procesado"}</strong>
                    <span>
                      {formatDate(analysis.created_at)} · {analysis.filename}
                    </span>
                  </div>
                  <StatusBadge tone={analysis.status === "success" ? "success" : "warn"}>
                    {analysis.status === "success" ? "Completo" : "Revisado"}
                  </StatusBadge>
                  <ArrowRight size={17} aria-hidden="true" />
                </Link>
              ))}
            </div>
          </section>
        </div>

        <aside className="dashboard-aside">
          <section className="pet-context-card">
            <div className="pet-context-card__intro">
              <PetAvatar pet={activePet} size="large" />
              <div>
                <p>Mascota activa</p>
                <h2>{activePet.name}</h2>
                <span>{activePet.breed}</span>
              </div>
            </div>
            <dl>
              <div>
                <dt>Edad aproximada</dt>
                <dd>
                  {typeof activePet.birth_year === "number"
                    ? `${new Date().getFullYear() - activePet.birth_year} años`
                    : "No indicada"}
                </dd>
              </div>
              <div>
                <dt>Peso registrado</dt>
                <dd>
                  {typeof activePet.weight_kg === "number"
                    ? `${activePet.weight_kg} kg`
                    : "No indicado"}
                </dd>
              </div>
              <div>
                <dt>Zona privada</dt>
                <dd>{activePet.residence_label ?? "No compartida"}</dd>
              </div>
            </dl>
            <Link
              className="button button--secondary button--full"
              to="/mascotas/$petId"
              params={{ petId: activePet.id }}
            >
              Ver perfil <ArrowRight size={17} aria-hidden="true" />
            </Link>
          </section>

          <section className="dashboard-panel quick-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Accesos</p>
                <h2>Continuar</h2>
              </div>
            </div>
            <div className="quick-list">
              <Link to="/mascotas/$petId/historial" params={{ petId: activePet.id }}>
                <CalendarDays size={19} aria-hidden="true" />
                <span>Historial de {activePet.name}</span>
                <ArrowRight size={16} />
              </Link>
              <Link to="/asistente">
                <Bot size={19} aria-hidden="true" />
                <span>Preguntar con contexto</span>
                <ArrowRight size={16} />
              </Link>
              <Link to="/biblioteca">
                <BookOpen size={19} aria-hidden="true" />
                <span>Buscar una definición</span>
                <ArrowRight size={16} />
              </Link>
            </div>
          </section>

          <section className="clinical-reminder">
            <CheckCircle2 size={20} aria-hidden="true" />
            <div>
              <strong>Antes de decidir</strong>
              <p>Comparte el informe original y el contexto completo con tu veterinario.</p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
