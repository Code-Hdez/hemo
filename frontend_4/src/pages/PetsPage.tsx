import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowRight, CalendarDays, Edit3, MapPin, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useAuth } from "../app/AuthContext";
import { api } from "../app/api";
import { useActivePet } from "../app/PetContext";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { PetAvatar } from "../components/PetAvatar";
import { PetFormModal, type PetFormSubmission } from "../components/PetFormModal";
import { PrivateFeatureGate } from "../components/PrivateFeatureGate";
import { StatePanel } from "../components/StatePanel";
import { StatusBadge } from "../components/StatusBadge";
import type { Pet, PetInput } from "../domain/types";

export function PetsPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { pets, loading, error: petsError, refetch: refetchPets } = useActivePet();
  const { data: breeds = [] } = useQuery({ queryKey: ["breeds"], queryFn: api.breeds });
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPet, setEditingPet] = useState<Pet | null>(null);
  const [error, setError] = useState("");
  const [savingPhoto, setSavingPhoto] = useState(false);

  const createMutation = useMutation({ mutationFn: api.createPet });
  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PetInput }) => api.updatePet(id, payload),
  });
  const deleteMutation = useMutation({ mutationFn: api.deletePet });

  async function refreshPetData(): Promise<void> {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["pets"] }),
      queryClient.invalidateQueries({ queryKey: ["pet"] }),
      queryClient.invalidateQueries({ queryKey: ["history"] }),
      queryClient.invalidateQueries({ queryKey: ["epidemiology"] }),
    ]);
  }

  async function save({ payload, photo, removePhoto }: PetFormSubmission): Promise<void> {
    setError("");
    let savedPet: Pet | undefined;
    try {
      savedPet = editingPet
        ? await updateMutation.mutateAsync({ id: editingPet.id, payload })
        : await createMutation.mutateAsync(payload);

      if (photo || (removePhoto && editingPet?.image)) {
        setSavingPhoto(true);
        try {
          if (photo) await api.uploadPetPhoto(savedPet.id, photo);
          else await api.deletePetPhoto(savedPet.id);
        } catch (photoError) {
          await refreshPetData();
          setError(
            `Se guardaron los datos de ${savedPet.name}, pero no se pudo actualizar la foto: ${
              photoError instanceof Error
                ? photoError.message
                : "inténtalo nuevamente desde Editar."
            }`,
          );
          setModalOpen(false);
          setEditingPet(null);
          return;
        } finally {
          setSavingPhoto(false);
        }
      }

      await refreshPetData();
      setModalOpen(false);
      setEditingPet(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible guardar la mascota.");
    }
  }

  async function remove(pet: Pet): Promise<void> {
    if (!window.confirm(`¿Eliminar a ${pet.name} y su asociación con el historial?`)) return;
    setError("");
    try {
      await deleteMutation.mutateAsync(pet.id);
      await refreshPetData();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible eliminar la mascota.");
    }
  }

  if (!user) {
    return (
      <PrivateFeatureGate description="Las mascotas registradas están disponibles cuando inicias sesión. En modo invitado puedes analizar un hemograma sin guardar historial." />
    );
  }

  if (loading) return <LoadingState label="Cargando mascotas" />;

  return (
    <div className="pets-page page-flow">
      <PageHeader
        eyebrow="Cuenta del propietario"
        title="Mascotas"
        description="Cada hemograma guardado debe asociarse con una mascota registrada."
        actions={
          <button
            className="button button--primary"
            type="button"
            data-tour="mascotas-registrar"
            onClick={() => {
              setEditingPet(null);
              setModalOpen(true);
            }}
          >
            <Plus size={18} aria-hidden="true" /> Registrar mascota
          </button>
        }
      />

      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}

      {petsError ? (
        <StatePanel
          icon={Plus}
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
      ) : pets.length === 0 ? (
        <StatePanel
          icon={Plus}
          title="Registra tu primera mascota"
          description="El perfil permitirá asociar cada hemograma y conservar su historial."
          action={
            <button
              className="button button--primary"
              type="button"
              onClick={() => {
                setEditingPet(null);
                setModalOpen(true);
              }}
            >
              <Plus size={18} aria-hidden="true" /> Registrar mascota
            </button>
          }
        />
      ) : (
        <div className="pet-list">
          {pets.map((pet) => (
            <article className="pet-row" key={pet.id}>
              <PetAvatar pet={pet} size="large" />
              <div className="pet-row__identity">
                <div>
                  <h2>{pet.name}</h2>
                  <StatusBadge tone={pet.residence_consent ? "success" : "neutral"}>
                    {pet.residence_consent ? "Vigilancia activa" : "Sin participación"}
                  </StatusBadge>
                </div>
                <p>
                  {pet.breed ?? "Raza no indicada"} · {pet.sex ?? "Sexo no indicado"} ·{" "}
                  {typeof pet.weight_kg === "number" ? `${pet.weight_kg} kg` : "Peso no indicado"}
                </p>
                <span>
                  <MapPin size={15} aria-hidden="true" />{" "}
                  {pet.residence_label ?? "Ubicación no compartida"}
                </span>
              </div>
              <div className="pet-row__notes">
                <span>Notas privadas</span>
                <p>{pet.notes || "Sin notas registradas."}</p>
              </div>
              <div className="pet-row__actions">
                <Link
                  className="button button--secondary"
                  to="/mascotas/$petId"
                  params={{ petId: pet.id }}
                >
                  Ver perfil <ArrowRight size={16} aria-hidden="true" />
                </Link>
                <Link
                  className="icon-button"
                  to="/mascotas/$petId/historial"
                  params={{ petId: pet.id }}
                  aria-label={`Abrir historial de ${pet.name}`}
                  title="Historial"
                >
                  <CalendarDays size={18} />
                </Link>
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => {
                    setEditingPet(pet);
                    setModalOpen(true);
                  }}
                  aria-label={`Editar a ${pet.name}`}
                  title="Editar"
                >
                  <Edit3 size={18} />
                </button>
                <button
                  className="icon-button icon-button--danger"
                  type="button"
                  onClick={() => remove(pet)}
                  aria-label={`Eliminar a ${pet.name}`}
                  title="Eliminar"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      <PetFormModal
        open={modalOpen}
        pet={editingPet}
        breeds={breeds}
        submitting={createMutation.isPending || updateMutation.isPending || savingPhoto}
        onClose={() => {
          setModalOpen(false);
          setEditingPet(null);
        }}
        onSubmit={save}
      />
    </div>
  );
}
