import { useMutation } from "@tanstack/react-query";
import {
  CircleAlert,
  ExternalLink,
  LoaderCircle,
  MapPinned,
  Search,
  Stethoscope,
} from "lucide-react";
import { useState } from "react";
import { api } from "../app/api";
import type { Pet } from "../domain/types";

const RADIUS_OPTIONS = [
  { value: 5_000, label: "5 km" },
  { value: 10_000, label: "10 km" },
  { value: 25_000, label: "25 km" },
] as const;

function formatDistance(distanceMeters: number): string {
  if (distanceMeters < 1_000) return `${Math.max(0, Math.round(distanceMeters))} m`;
  return `${(distanceMeters / 1_000).toLocaleString("es-DO", {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1,
  })} km`;
}

interface NearbyVeterinaryCarePanelProps {
  pet: Pet;
  petOptions?: Pet[];
  onPetChange?: (petId: string) => void;
}

export function NearbyVeterinaryCarePanel({
  pet,
  petOptions,
  onPetChange,
}: NearbyVeterinaryCarePanelProps): React.JSX.Element {
  const [radiusMeters, setRadiusMeters] = useState(10_000);
  const hasApproximateLocation =
    pet.residence_consent &&
    typeof pet.residence_lat === "number" &&
    typeof pet.residence_lng === "number";
  const nearbyCare = useMutation({
    mutationFn: () =>
      api.nearbyVeterinaryCare({
        pet_id: pet.id,
        radius_meters: radiusMeters,
      }),
  });

  return (
    <section className="dashboard-panel veterinary-care-panel" aria-labelledby="nearby-care-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Mapa y orientación</p>
          <h2 id="nearby-care-title">Atención veterinaria cercana</h2>
        </div>
        <Stethoscope size={21} aria-hidden="true" />
      </div>

      <p>
        Busca centros publicados en OpenStreetMap usando únicamente la zona aproximada guardada para{" "}
        {pet.name}. La ubicación exacta de tu mascota no se comparte.
      </p>

      <form
        className="veterinary-care-controls"
        onSubmit={(event) => {
          event.preventDefault();
          nearbyCare.mutate();
        }}
      >
        {petOptions && petOptions.length > 0 && onPetChange && (
          <label className="veterinary-care-pet-field" htmlFor={`nearby-care-pet-${pet.id}`}>
            Mascota
            <select
              id={`nearby-care-pet-${pet.id}`}
              value={pet.id}
              onChange={(event) => onPetChange(event.target.value)}
            >
              {petOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                  {option.residence_label ? ` — ${option.residence_label}` : " — sin zona"}
                </option>
              ))}
            </select>
          </label>
        )}
        <label htmlFor={`nearby-care-radius-${pet.id}`}>
          Radio de búsqueda
          <select
            id={`nearby-care-radius-${pet.id}`}
            value={radiusMeters}
            onChange={(event) => {
              setRadiusMeters(Number(event.target.value));
              nearbyCare.reset();
            }}
          >
            {RADIUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <button
          className="button button--secondary"
          type="submit"
          disabled={!hasApproximateLocation || nearbyCare.isPending}
        >
          {nearbyCare.isPending ? (
            <LoaderCircle className="spin" size={17} aria-hidden="true" />
          ) : (
            <Search size={17} aria-hidden="true" />
          )}
          {nearbyCare.isPending ? "Buscando…" : "Buscar centros"}
        </button>
      </form>

      {!hasApproximateLocation && (
        <output className="veterinary-care-notice" data-tone="warning">
          <CircleAlert size={18} aria-hidden="true" />
          <p>
            Registra y autoriza una zona aproximada para habilitar esta búsqueda desde el perfil de
            la mascota.
          </p>
        </output>
      )}

      {nearbyCare.isError && (
        <div className="veterinary-care-notice" data-tone="error" role="alert">
          <CircleAlert size={18} aria-hidden="true" />
          <div>
            <strong>No fue posible completar la búsqueda.</strong>
            <p>
              {nearbyCare.error instanceof Error
                ? nearbyCare.error.message
                : "Inténtalo nuevamente en unos minutos."}
            </p>
          </div>
        </div>
      )}

      {nearbyCare.data && (
        <div className="veterinary-care-results" aria-live="polite">
          <div className="veterinary-care-results__summary">
            <div>
              <strong>
                {nearbyCare.data.items.length
                  ? nearbyCare.data.items.length === 1
                    ? "1 centro encontrado"
                    : `${nearbyCare.data.items.length} centros encontrados`
                  : "Sin centros confirmados"}
              </strong>
              <p>{nearbyCare.data.message}</p>
            </div>
            <a
              className="button button--ghost"
              href={nearbyCare.data.search_url}
              target="_blank"
              rel="noreferrer"
            >
              Abrir búsqueda general
              <ExternalLink size={16} aria-hidden="true" />
            </a>
          </div>

          {nearbyCare.data.items.length > 0 && (
            <ol className="veterinary-place-list" aria-label="Centros veterinarios cercanos">
              {nearbyCare.data.items.map((place) => (
                <li key={`${place.osm_url}-${place.lat}-${place.lng}`}>
                  <span className="veterinary-place-list__icon">
                    <MapPinned size={19} aria-hidden="true" />
                  </span>
                  <div>
                    <strong>{place.name}</strong>
                    <p>{place.address ?? "Dirección no publicada"}</p>
                    <span>{formatDistance(place.distance_meters)} desde la zona aproximada</span>
                  </div>
                  <a
                    className="icon-button"
                    href={place.osm_url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`Abrir ${place.name} en OpenStreetMap`}
                    title="Abrir en OpenStreetMap"
                  >
                    <ExternalLink size={17} aria-hidden="true" />
                  </a>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      <div className="privacy-row veterinary-care-disclaimer">
        <CircleAlert size={18} aria-hidden="true" />
        <span>
          Verifica horario y disponibilidad antes de trasladarte. Si hay signos graves, busca
          atención veterinaria urgente.
        </span>
      </div>
    </section>
  );
}
