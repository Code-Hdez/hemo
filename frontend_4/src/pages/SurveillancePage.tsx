import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { CalendarDays, Eye, Info, MapPinOff, PawPrint, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../app/AuthContext";
import { api } from "../app/api";
import { useActivePet } from "../app/PetContext";
import { LoadingState } from "../components/LoadingState";
import { NearbyVeterinaryCarePanel } from "../components/NearbyVeterinaryCarePanel";
import { PageHeader } from "../components/PageHeader";
import { PrivateFeatureGate } from "../components/PrivateFeatureGate";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import { SurveillanceMap } from "../components/SurveillanceMap";
import { formatActivityCount, formatActivityPeriod, intensityLabel } from "../domain/surveillance";

export function SurveillancePage(): React.JSX.Element {
  const { user } = useAuth();
  const {
    pets,
    activePet,
    setActivePetId,
    loading: petsLoading,
    error: petsError,
    refetch: refetchPets,
  } = useActivePet();
  const [period, setPeriod] = useState(90);
  const queryClient = useQueryClient();
  const pointsQuery = useQuery({
    queryKey: ["epidemiology", period],
    queryFn: () => api.epidemiology(period),
    enabled: Boolean(user),
  });
  const temporalQuery = useQuery({
    queryKey: ["temporal-analytics", period],
    queryFn: () => api.temporalAnalytics(period),
    enabled: Boolean(user),
  });
  const data = pointsQuery.data ?? [];

  useEffect(() => {
    if (!user) return;
    const refresh = () => void queryClient.invalidateQueries({ queryKey: ["epidemiology"] });
    const liveStreamAvailable =
      typeof EventSource !== "undefined" && import.meta.env.VITE_ENABLE_MSW !== "true";
    if (!liveStreamAvailable) {
      const timer = window.setInterval(refresh, 25_000);
      return () => window.clearInterval(timer);
    }
    const source = new EventSource(api.epidemiologyStreamUrl());
    source.addEventListener("snapshot", refresh);
    source.addEventListener("map_updated", refresh);
    source.onerror = () => refresh();
    return () => {
      source.removeEventListener("snapshot", refresh);
      source.removeEventListener("map_updated", refresh);
      source.close();
    };
  }, [queryClient, user]);

  if (!user) {
    return (
      <PrivateFeatureGate
        icon={MapPinOff}
        description="El mapa poblacional está disponible para cuentas registradas. En modo invitado puedes analizar un hemograma y ver el resultado puntual del modelo."
      />
    );
  }

  return (
    <div className="surveillance-page page-flow">
      <PageHeader
        eyebrow="Vigilancia comunitaria"
        title="Lo que se observa en tu comunidad"
        description="Consulta de forma anónima los hallazgos más frecuentes en hemogramas registrados cerca de tu zona."
        actions={
          <fieldset className="segmented-control">
            <legend className="sr-only">Periodo del mapa</legend>
            {[30, 90].map((days) => (
              <button
                key={days}
                type="button"
                data-active={period === days}
                onClick={() => setPeriod(days)}
              >
                {days} días
              </button>
            ))}
          </fieldset>
        }
      />

      <section className="surveillance-method" data-tour="vigilancia-mapa">
        <ShieldCheck size={21} aria-hidden="true" />
        <div>
          <strong>Tu ubicación permanece protegida</strong>
          <p>
            Una zona solo aparece cuando al menos 3 mascotas han aportado información con
            consentimiento. Nunca mostramos direcciones ni ubicaciones exactas.
          </p>
        </div>
        <Info size={19} aria-hidden="true" />
        <p>
          Esta información es orientativa. Solo un veterinario puede interpretar el estado de salud
          de una mascota.
        </p>
      </section>

      {petsLoading ? (
        <LoadingState label="Cargando mascotas para la búsqueda veterinaria" />
      ) : petsError ? (
        <StatePanel
          icon={PawPrint}
          title="No fue posible cargar tus mascotas"
          description={petsError.message}
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
      ) : activePet ? (
        <NearbyVeterinaryCarePanel
          key={activePet.id}
          pet={activePet}
          petOptions={pets}
          onPetChange={setActivePetId}
        />
      ) : (
        <StatePanel
          icon={PawPrint}
          title="Registra una mascota para buscar atención cercana"
          description="La búsqueda utiliza únicamente una zona aproximada autorizada y nunca publica una dirección exacta."
          action={
            <Link className="button button--primary" to="/mascotas">
              Registrar mascota
            </Link>
          }
        />
      )}

      {pointsQuery.isLoading ? (
        <LoadingState label="Cargando zonas agregadas" />
      ) : pointsQuery.error ? (
        <StatePanel
          icon={MapPinOff}
          title="No fue posible cargar la vigilancia"
          description={pointsQuery.error.message}
          tone="error"
          action={
            <button
              className="button button--secondary"
              type="button"
              onClick={() => void pointsQuery.refetch()}
            >
              Reintentar
            </button>
          }
        />
      ) : data.length === 0 ? (
        <StatePanel
          icon={MapPinOff}
          title="No hay zonas visibles en este periodo"
          description="Ninguna zona cumple todavía los mínimos de reportes, mascotas y consentimiento requeridos para proteger la privacidad."
        />
      ) : (
        <div className="surveillance-layout">
          <section className="map-panel">
            <div className="map-panel__top">
              <section className="map-legend" aria-label="Leyenda de intensidad">
                <span data-level="low">Pocos registros</span>
                <span data-level="moderate">Varios registros</span>
                <span data-level="high">Más registros</span>
              </section>
              <span className="live-indicator">
                <Eye size={15} aria-hidden="true" /> Información actualizada
              </span>
            </div>
            <SurveillanceMap points={data} />
          </section>

          <aside className="zone-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Zonas visibles</p>
                <h2>{data.length === 1 ? "1 zona" : `${data.length} zonas`}</h2>
              </div>
            </div>
            <div className="zone-list">
              {data.map((point) => (
                <article key={point.zone_code ?? `${point.lat}-${point.lng}`}>
                  <span className="zone-dot" data-level={point.intensity_level ?? "low"} />
                  <div>
                    <strong>{point.zone_label ?? point.location_name}</strong>
                    <p>{point.finding}</p>
                    <span>
                      {formatActivityCount(point.report_count ?? point.count)} ·{" "}
                      {point.pet_count ?? 0} {(point.pet_count ?? 0) === 1 ? "mascota" : "mascotas"}
                    </span>
                  </div>
                  <StatusBadge
                    tone={
                      point.intensity_level === "high"
                        ? "danger"
                        : point.intensity_level === "moderate"
                          ? "warn"
                          : "info"
                    }
                  >
                    {intensityLabel(point.intensity_level)}
                  </StatusBadge>
                </article>
              ))}
            </div>
          </aside>
        </div>
      )}

      {data.length > 0 && (
        <section className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Alternativa textual</p>
              <h2>Datos equivalentes al mapa</h2>
            </div>
          </div>
          <section
            className="table-wrap"
            aria-label="Datos tabulares equivalentes al mapa"
            // biome-ignore lint/a11y/noNoninteractiveTabindex: Scrollable table regions must be keyboard focusable.
            tabIndex={0}
          >
            <table className="data-table">
              <thead>
                <tr>
                  <th>Zona</th>
                  <th>Hallazgo más frecuente</th>
                  <th>Hemogramas</th>
                  <th>Mascotas</th>
                  <th>Cantidad de registros</th>
                </tr>
              </thead>
              <tbody>
                {data.map((point) => (
                  <tr key={point.zone_code ?? `${point.lat}-${point.lng}`}>
                    <th scope="row">{point.zone_label ?? point.location_name}</th>
                    <td>{point.finding}</td>
                    <td>{point.report_count ?? point.count}</td>
                    <td>{point.pet_count ?? 0}</td>
                    <td>{intensityLabel(point.intensity_level)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </section>
      )}

      {temporalQuery.data && temporalQuery.data.timeline.length > 0 && (
        <section className="dashboard-panel activity-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Actividad reciente</p>
              <h2>Hemogramas registrados en los últimos {period} días</h2>
            </div>
          </div>
          <div className="temporal-list">
            {temporalQuery.data.timeline.slice(-6).map((item) => (
              <article key={item.period}>
                <div className="temporal-list__period">
                  <CalendarDays size={19} aria-hidden="true" />
                  <div>
                    <small>Período</small>
                    <strong>{formatActivityPeriod(item.period)}</strong>
                  </div>
                </div>
                <div className="temporal-list__finding">
                  <small>Hallazgo más frecuente</small>
                  <strong>{item.top_finding}</strong>
                </div>
                <span className="temporal-list__count">{formatActivityCount(item.n_analyses)}</span>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
