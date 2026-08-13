import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "@tanstack/react-router";
import {
  ArrowRight,
  CalendarDays,
  ClipboardPlus,
  MapPin,
  PawPrint,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "../app/AuthContext";
import { api } from "../app/api";
import { LoadingState } from "../components/LoadingState";
import { NearbyVeterinaryCarePanel } from "../components/NearbyVeterinaryCarePanel";
import { PageHeader } from "../components/PageHeader";
import { PetAvatar } from "../components/PetAvatar";
import { PrivateFeatureGate } from "../components/PrivateFeatureGate";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";

export function PetDetailPage(): React.JSX.Element {
  const { user } = useAuth();
  const { petId } = useParams({ strict: false }) as { petId: string };
  const {
    data: pet,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["pet", petId],
    queryFn: () => api.pet(petId),
    enabled: Boolean(user),
  });
  const { data: history = [] } = useQuery({
    queryKey: ["history", petId],
    queryFn: () => api.history({ petId }),
    enabled: Boolean(user),
  });

  if (!user) {
    return (
      <PrivateFeatureGate
        icon={PawPrint}
        description="Los perfiles de mascotas requieren iniciar sesión. En modo invitado puedes analizar un hemograma sin asociarlo a una mascota."
      />
    );
  }

  if (isLoading) return <LoadingState label="Cargando perfil" />;
  if (error || !pet) {
    return (
      <StatePanel
        icon={PawPrint}
        title="No fue posible abrir esta mascota"
        description="El perfil solicitado no está disponible o no pudo cargarse."
        tone="error"
        action={
          <button className="button button--secondary" type="button" onClick={() => void refetch()}>
            Reintentar
          </button>
        }
      />
    );
  }

  return (
    <div className="pet-detail-page page-flow">
      <PageHeader
        eyebrow="Perfil de mascota"
        title={pet.name}
        description="Información privada utilizada para asociar hemogramas y contextualizar el historial."
        actions={
          <Link className="button button--primary" to="/analisis/nuevo">
            <ClipboardPlus size={18} aria-hidden="true" /> Nuevo hemograma
          </Link>
        }
      />
      <div className="pet-detail-layout">
        <section className="pet-profile-panel">
          <PetAvatar pet={pet} size="large" />
          <div>
            <h2>{pet.name}</h2>
            <p>{pet.breed}</p>
            <StatusBadge tone={pet.residence_consent ? "success" : "neutral"}>
              {pet.residence_consent ? "Participa con datos agregados" : "No participa"}
            </StatusBadge>
          </div>
          <dl>
            <div>
              <dt>Año de nacimiento</dt>
              <dd>{pet.birth_year}</dd>
            </div>
            <div>
              <dt>Sexo</dt>
              <dd>{pet.sex}</dd>
            </div>
            <div>
              <dt>Peso</dt>
              <dd>{pet.weight_kg} kg</dd>
            </div>
            <div>
              <dt>Hemogramas</dt>
              <dd>{history.length}</dd>
            </div>
          </dl>
        </section>

        <div className="pet-detail-main">
          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Seguimiento</p>
                <h2>Historial cronológico</h2>
              </div>
              <CalendarDays size={21} aria-hidden="true" />
            </div>
            <p>
              Consulta cada hemograma de forma individual y observa los valores registrados a lo
              largo del tiempo.
            </p>
            <Link
              className="button button--secondary"
              to="/mascotas/$petId/historial"
              params={{ petId: pet.id }}
            >
              Abrir historial <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </section>

          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Residencia</p>
                <h2>Zona protegida</h2>
              </div>
              <MapPin size={21} aria-hidden="true" />
            </div>
            <p>{pet.residence_label ?? "No compartida para vigilancia comunitaria."}</p>
            <div className="privacy-row">
              <ShieldCheck size={18} aria-hidden="true" />
              <span>
                {pet.residence_consent
                  ? `Precisión guardada: ${pet.residence_precision}. El mapa público aplica una agregación adicional.`
                  : "Esta mascota no comparte ubicación con el mapa comunitario."}
              </span>
            </div>
          </section>

          <NearbyVeterinaryCarePanel key={pet.id} pet={pet} />

          <section className="dashboard-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Notas</p>
                <h2>Contexto privado</h2>
              </div>
            </div>
            <p>{pet.notes || "Sin notas registradas."}</p>
          </section>
        </div>
      </div>
    </div>
  );
}
