import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { LoaderCircle, MapPin, ScanLine, Search, ShieldCheck, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Dialog, Heading, Modal, ModalOverlay } from "react-aria-components";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../app/api";
import defaultPetImage from "../assets/dog-head-profile.svg";
import { isValidProperName, normalizeSingleLineText } from "../domain/formValidation";
import { suggestedPetProfileFromExtraction } from "../domain/petProfile";
import type { Pet, PetInput, ResidenceCandidate } from "../domain/types";
import { ResidenceMapPicker, type ResidencePosition } from "./ResidenceMapPicker";

const currentYear = new Date().getFullYear();
const PROFILE_LOADER_CELLS = Array.from({ length: 8 }, (_, index) => `profile-cell-${index + 1}`);
const petNameSchema = z
  .string()
  .transform(normalizeSingleLineText)
  .pipe(
    z
      .string()
      .min(2, "El nombre de la mascota es obligatorio.")
      .max(100, "Usa 100 caracteres o menos.")
      .refine(isValidProperName, "El nombre no puede contener números ni símbolos."),
  );
const breedSchema = z
  .string()
  .transform(normalizeSingleLineText)
  .pipe(
    z
      .string()
      .min(2, "La raza es obligatoria.")
      .max(150, "Usa 150 caracteres o menos.")
      .refine(isValidProperName, "La raza no puede contener números ni símbolos."),
  );

const schema = z
  .object({
    name: petNameSchema,
    breed: breedSchema,
    birth_year: z.number().min(1990).max(currentYear),
    sex: z.enum(["Hembra", "Macho"]),
    weight_kg: z.number().min(0.5).max(120),
    notes: z
      .string()
      .transform((value) => value.trim())
      .pipe(z.string().max(2000)),
    residence_zone_code: z.string().transform(normalizeSingleLineText).optional(),
    residence_lat: z.number().finite().optional(),
    residence_lng: z.number().finite().optional(),
    residence_source: z.enum(["address", "pin", "catalog"]).optional(),
    residence_consent: z.boolean(),
  })
  .superRefine((values, context) => {
    const hasPin =
      typeof values.residence_lat === "number" && typeof values.residence_lng === "number";
    const hasZone = Boolean(values.residence_zone_code?.trim());

    if (!hasPin && !hasZone) {
      context.addIssue({
        code: "custom",
        path: ["residence_zone_code"],
        message: "La ubicación es obligatoria.",
      });
    }
    if (!values.residence_consent) {
      context.addIssue({
        code: "custom",
        path: ["residence_consent"],
        message: "Confirma el consentimiento para registrar la ubicación agregada.",
      });
    }
  });

type FormValues = z.infer<typeof schema>;

export interface PetFormSubmission {
  payload: PetInput;
  photo?: File;
  removePhoto: boolean;
}

export type PetFormInitialValues = Partial<
  Pick<PetInput, "name" | "breed" | "birth_year" | "sex" | "weight_kg" | "notes">
>;

interface PetFormModalProps {
  open: boolean;
  pet?: Pet | null;
  initialValues?: PetFormInitialValues;
  breeds: string[];
  submitting: boolean;
  onClose: () => void;
  onSubmit: (submission: PetFormSubmission) => Promise<void>;
}

function RequiredMark(): React.JSX.Element {
  return (
    <span className="required-mark" aria-hidden="true">
      {" "}
      (*)
    </span>
  );
}

export function PetFormModal({
  open,
  pet,
  initialValues,
  breeds,
  submitting,
  onClose,
  onSubmit,
}: PetFormModalProps): React.JSX.Element {
  const {
    register,
    reset,
    handleSubmit,
    watch,
    setValue,
    getFieldState,
    clearErrors,
    trigger,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: "onChange",
    reValidateMode: "onChange",
    defaultValues: {
      name: "",
      breed: "",
      birth_year: initialValues?.birth_year ?? 2020,
      sex: initialValues?.sex ?? "Hembra",
      weight_kg: initialValues?.weight_kg ?? 10,
      notes: "",
      residence_zone_code: "",
      residence_consent: false,
    },
  });
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | undefined>();
  const [removePhoto, setRemovePhoto] = useState(false);
  const [photoError, setPhotoError] = useState("");
  const [addressQuery, setAddressQuery] = useState("");
  const [candidates, setCandidates] = useState<ResidenceCandidate[]>([]);
  const [addressError, setAddressError] = useState("");
  const [searching, setSearching] = useState(false);
  const [profileFileName, setProfileFileName] = useState("");
  const [profileExtracting, setProfileExtracting] = useState(false);
  const [profileExtractedFields, setProfileExtractedFields] = useState<string[]>([]);
  const [profileError, setProfileError] = useState("");
  const { data: zones = [] } = useQuery({
    queryKey: ["residence-zones"],
    queryFn: api.residenceZones,
    enabled: open,
    staleTime: 5 * 60_000,
  });
  const residenceLat = watch("residence_lat");
  const residenceLng = watch("residence_lng");
  const residenceConsent = watch("residence_consent");
  const zoneField = register("residence_zone_code");
  const consentField = register("residence_consent");
  const selectedPosition: ResidencePosition | null =
    typeof residenceLat === "number" && typeof residenceLng === "number"
      ? { lat: residenceLat, lng: residenceLng }
      : null;
  const formLocked = submitting || profileExtracting;
  const birthYears = Array.from(
    { length: currentYear - 2000 + 1 },
    (_, index) => currentYear - index,
  );

  useEffect(() => {
    if (!open) return;
    reset({
      name: pet?.name ?? initialValues?.name ?? "",
      breed: pet?.breed ?? initialValues?.breed ?? "",
      birth_year: pet?.birth_year ?? initialValues?.birth_year ?? 2020,
      sex:
        pet?.sex === "Macho" || pet?.sex === "Hembra" ? pet.sex : (initialValues?.sex ?? "Hembra"),
      weight_kg: pet?.weight_kg ?? initialValues?.weight_kg ?? 10,
      notes: pet?.notes ?? initialValues?.notes ?? "",
      residence_zone_code: pet?.residence_zone_code ?? "",
      residence_lat: pet?.residence_lat ?? undefined,
      residence_lng: pet?.residence_lng ?? undefined,
      residence_source:
        typeof pet?.residence_lat === "number" && typeof pet?.residence_lng === "number"
          ? "pin"
          : "catalog",
      residence_consent: pet?.residence_consent ?? false,
    });
    setPhotoFile(null);
    setPhotoPreviewUrl(undefined);
    setRemovePhoto(false);
    setPhotoError("");
    setAddressQuery("");
    setCandidates([]);
    setAddressError("");
    setProfileFileName("");
    setProfileExtracting(false);
    setProfileExtractedFields([]);
    setProfileError("");
  }, [open, pet, initialValues, reset]);

  useEffect(() => {
    if (!photoFile) return undefined;
    const objectUrl = URL.createObjectURL(photoFile);
    setPhotoPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [photoFile]);

  function setPin(position: ResidencePosition): void {
    setValue("residence_lat", position.lat, { shouldDirty: true, shouldValidate: true });
    setValue("residence_lng", position.lng, { shouldDirty: true, shouldValidate: true });
    setValue("residence_source", "pin", { shouldDirty: true });
    setValue("residence_zone_code", "", { shouldDirty: true, shouldValidate: true });
    clearErrors("residence_zone_code");
    void trigger(["residence_zone_code", "residence_consent"]);
  }

  function clearPin(): void {
    setValue("residence_lat", undefined, { shouldDirty: true, shouldValidate: true });
    setValue("residence_lng", undefined, { shouldDirty: true, shouldValidate: true });
    setValue("residence_source", undefined, { shouldDirty: true });
    void trigger(["residence_zone_code", "residence_consent"]);
  }

  async function searchAddress(): Promise<void> {
    const value = addressQuery.trim();
    if (value.length < 3) {
      setAddressError("Escribe una dirección o sector con al menos 3 caracteres.");
      return;
    }
    setSearching(true);
    setAddressError("");
    try {
      const result = await api.resolveResidence(value);
      setCandidates(result);
      if (result.length === 0)
        setAddressError("No encontramos esa dirección. Puedes marcar el mapa.");
    } catch (error) {
      setCandidates([]);
      setAddressError(
        error instanceof Error ? error.message : "No fue posible buscar la dirección.",
      );
    } finally {
      setSearching(false);
    }
  }

  function selectAddress(candidate: ResidenceCandidate): void {
    setAddressQuery(candidate.label);
    setCandidates([]);
    setAddressError("");
    setPin({ lat: candidate.lat, lng: candidate.lng });
    setValue("residence_source", "address", { shouldDirty: true });
  }

  function selectPhoto(file: File | undefined): void {
    if (!file) return;
    const isAllowedType = ["image/jpeg", "image/png", "image/webp"].includes(file.type);
    const isAllowedExtension = /\.(jpe?g|png|webp)$/i.test(file.name);
    if (!isAllowedType && !isAllowedExtension) {
      setPhotoError("Selecciona una imagen JPG, PNG o WebP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setPhotoError("La foto no puede superar 5 MiB.");
      return;
    }
    setPhotoError("");
    setPhotoFile(file);
    setRemovePhoto(false);
  }

  async function extractPetProfile(file: File | undefined): Promise<void> {
    if (!file) return;
    setProfileFileName(file.name);
    setProfileExtracting(true);
    setProfileError("");
    setProfileExtractedFields([]);
    try {
      const profile = await api.extractPetProfile(file);
      const suggestion = suggestedPetProfileFromExtraction(profile);
      if (suggestion.values.name && !getFieldState("name").isDirty) {
        setValue("name", suggestion.values.name, { shouldDirty: true, shouldValidate: true });
      }
      if (suggestion.values.breed && !getFieldState("breed").isDirty) {
        setValue("breed", suggestion.values.breed, { shouldDirty: true, shouldValidate: true });
      }
      if (suggestion.values.birth_year && !getFieldState("birth_year").isDirty) {
        setValue("birth_year", suggestion.values.birth_year, {
          shouldDirty: true,
          shouldValidate: true,
        });
      }
      if (suggestion.values.sex && !getFieldState("sex").isDirty) {
        setValue("sex", suggestion.values.sex, { shouldDirty: true, shouldValidate: true });
      }
      if (suggestion.values.weight_kg && !getFieldState("weight_kg").isDirty) {
        setValue("weight_kg", suggestion.values.weight_kg, {
          shouldDirty: true,
          shouldValidate: true,
        });
      }
      if (suggestion.values.notes && !getFieldState("notes").isDirty) {
        setValue("notes", suggestion.values.notes, { shouldDirty: true, shouldValidate: true });
      }
      setProfileExtractedFields(profile.detected_fields);
      if (profile.detected_fields.length === 0) {
        setProfileError("Gemini no encontró datos claros para completar el formulario.");
      }
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "No fue posible analizar la ficha.");
    } finally {
      setProfileExtracting(false);
    }
  }

  return (
    <ModalOverlay
      className="modal-overlay"
      isOpen={open}
      onOpenChange={(value) => !value && onClose()}
    >
      <Modal className="modal">
        <Dialog className="dialog" aria-label={pet ? `Editar a ${pet.name}` : "Registrar mascota"}>
          <div className="dialog__header">
            <div>
              <p className="eyebrow">{pet ? "Editar datos" : "Nueva mascota"}</p>
              <Heading slot="title">{pet ? pet.name : "Registrar mascota"}</Heading>
            </div>
            <button
              className="icon-button"
              type="button"
              onClick={onClose}
              aria-label="Cerrar formulario"
            >
              <X size={19} />
            </button>
          </div>
          <form
            className="pet-form"
            onSubmit={handleSubmit(async (values) => {
              await onSubmit({
                payload: {
                  ...values,
                  residence_zone_code: values.residence_zone_code?.trim() || undefined,
                  residence_lat: values.residence_lat,
                  residence_lng: values.residence_lng,
                  residence_source: values.residence_source,
                },
                photo: photoFile ?? undefined,
                removePhoto,
              });
            })}
          >
            <div className="pet-form__body">
              <section className="pet-photo-field" aria-labelledby="pet-photo-label">
                <img
                  className="pet-photo-field__preview"
                  src={
                    removePhoto
                      ? defaultPetImage
                      : (photoPreviewUrl ?? pet?.image ?? defaultPetImage)
                  }
                  alt="Vista previa de la foto de perfil de la mascota"
                />
                <div>
                  <strong id="pet-photo-label">Foto de perfil</strong>
                  <p>Opcional. JPG, PNG o WebP; tamaño máximo de 5 MiB.</p>
                  <div className="pet-photo-field__actions">
                    <label className="button button--secondary" htmlFor="pet-profile-photo">
                      {photoFile
                        ? "Cambiar foto"
                        : pet?.image && !removePhoto
                          ? "Reemplazar foto"
                          : "Seleccionar foto"}
                    </label>
                    <input
                      id="pet-profile-photo"
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      disabled={formLocked}
                      onChange={(event) => {
                        selectPhoto(event.target.files?.[0]);
                        event.currentTarget.value = "";
                      }}
                    />
                    {photoFile && (
                      <button
                        className="button button--ghost"
                        type="button"
                        disabled={formLocked}
                        onClick={() => {
                          setPhotoFile(null);
                          setPhotoError("");
                        }}
                      >
                        Descartar selección
                      </button>
                    )}
                    {pet?.image && !photoFile && !removePhoto && (
                      <button
                        className="button button--ghost"
                        type="button"
                        disabled={formLocked}
                        onClick={() => setRemovePhoto(true)}
                      >
                        Quitar foto
                      </button>
                    )}
                    {pet?.image && removePhoto && (
                      <button
                        className="button button--ghost"
                        type="button"
                        disabled={formLocked}
                        onClick={() => setRemovePhoto(false)}
                      >
                        Conservar foto actual
                      </button>
                    )}
                  </div>
                  {photoError && <small className="field-error">{photoError}</small>}
                </div>
              </section>

              {!pet && (
                <section
                  className="medical-profile-field"
                  aria-labelledby="medical-profile-title"
                  aria-busy={profileExtracting}
                >
                  <div>
                    <span className="eyebrow">Ficha médica</span>
                    <h3 id="medical-profile-title">Prellenar con imagen de ficha</h3>
                    <p>
                      Sube una foto clara de la ficha. Gemini intentará detectar nombre, raza, edad,
                      sexo y peso sin guardar la imagen.
                    </p>
                    {profileExtracting && (
                      <output className="medical-profile-loading" aria-live="polite">
                        <div className="medical-profile-loading__visual" aria-hidden="true">
                          {PROFILE_LOADER_CELLS.map((cell) => (
                            <span key={cell} />
                          ))}
                          <i />
                        </div>
                        <span>Analizando la ficha. Los campos se desbloquean al terminar.</span>
                      </output>
                    )}
                    {profileFileName && <small title={profileFileName}>{profileFileName}</small>}
                    {profileExtractedFields.length > 0 && (
                      <small>Detectado: {profileExtractedFields.join(", ")}.</small>
                    )}
                    {profileError && <small className="field-error">{profileError}</small>}
                  </div>
                  <label
                    className="button button--secondary"
                    data-disabled={formLocked}
                    htmlFor="pet-medical-profile"
                  >
                    {profileExtracting ? (
                      <LoaderCircle size={17} aria-hidden="true" />
                    ) : (
                      <ScanLine size={17} aria-hidden="true" />
                    )}
                    {profileExtracting ? "Analizando..." : "Analizar ficha"}
                  </label>
                  <input
                    id="pet-medical-profile"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/tiff"
                    disabled={formLocked}
                    onChange={(event) => {
                      void extractPetProfile(event.target.files?.[0]);
                      event.currentTarget.value = "";
                    }}
                  />
                </section>
              )}

              <fieldset className="form-grid" disabled={formLocked}>
                <label>
                  <span>
                    Nombre
                    <RequiredMark />
                  </span>
                  <input
                    {...register("name")}
                    autoComplete="off"
                    aria-invalid={Boolean(errors.name)}
                  />
                  {errors.name && <small className="field-error">{errors.name.message}</small>}
                </label>
                <label>
                  <span>
                    Raza
                    <RequiredMark />
                  </span>
                  <input
                    {...register("breed")}
                    list="breed-options"
                    autoComplete="off"
                    aria-invalid={Boolean(errors.breed)}
                  />
                  <datalist id="breed-options">
                    {breeds.map((breed) => (
                      <option key={breed} value={breed} />
                    ))}
                  </datalist>
                  {errors.breed && <small className="field-error">{errors.breed.message}</small>}
                </label>
                <label>
                  <span>
                    Año de nacimiento
                    <RequiredMark />
                  </span>
                  <select
                    {...register("birth_year", { valueAsNumber: true })}
                    aria-invalid={Boolean(errors.birth_year)}
                  >
                    {birthYears.map((year) => (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    ))}
                  </select>
                  {errors.birth_year && (
                    <small className="field-error">Selecciona un año válido.</small>
                  )}
                </label>
                <label>
                  <span>
                    Sexo
                    <RequiredMark />
                  </span>
                  <select {...register("sex")} aria-invalid={Boolean(errors.sex)}>
                    <option value="Hembra">Hembra</option>
                    <option value="Macho">Macho</option>
                  </select>
                </label>
                <label>
                  <span>
                    Peso aproximado (kg)
                    <RequiredMark />
                  </span>
                  <input
                    type="number"
                    step="0.1"
                    {...register("weight_kg", { valueAsNumber: true })}
                    aria-invalid={Boolean(errors.weight_kg)}
                  />
                  {errors.weight_kg && (
                    <small className="field-error">
                      Ingresa un peso válido entre 0.5 y 120 kg.
                    </small>
                  )}
                </label>
                <label>
                  <span>
                    Zona aproximada
                    <RequiredMark />
                  </span>
                  <select
                    name={zoneField.name}
                    ref={zoneField.ref}
                    onBlur={zoneField.onBlur}
                    aria-invalid={Boolean(errors.residence_zone_code)}
                    onChange={(event) => {
                      setValue("residence_zone_code", event.target.value, {
                        shouldDirty: true,
                        shouldValidate: true,
                      });
                      clearPin();
                      setValue("residence_source", event.target.value ? "catalog" : undefined, {
                        shouldDirty: true,
                        shouldValidate: true,
                      });
                      if (event.target.value) clearErrors("residence_zone_code");
                      void trigger(["residence_zone_code", "residence_consent"]);
                    }}
                  >
                    <option value="">Selecciona una zona o marca un punto</option>
                    {zones.map((zone) => (
                      <option key={zone.code} value={zone.code}>
                        {zone.label}
                      </option>
                    ))}
                  </select>
                  {errors.residence_zone_code && (
                    <small className="field-error">{errors.residence_zone_code.message}</small>
                  )}
                </label>
              </fieldset>

              <section className="residence-picker" aria-labelledby="residence-search-title">
                <div className="residence-picker__heading">
                  <div>
                    <span className="eyebrow">Buscar dirección</span>
                    <h3 id="residence-search-title">Encuentra un sector aproximado</h3>
                  </div>
                  <Search size={21} aria-hidden="true" />
                </div>
                <div className="residence-search-control">
                  <input
                    aria-label="Buscar dirección o sector"
                    value={addressQuery}
                    disabled={formLocked}
                    onChange={(event) => {
                      setAddressQuery(event.target.value);
                      if (addressError) setAddressError("");
                    }}
                    placeholder="Ej. Los Jardines, Santiago"
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        void searchAddress();
                      }
                    }}
                  />
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => void searchAddress()}
                    disabled={searching || formLocked}
                    aria-label="Buscar dirección"
                  >
                    <Search size={18} />
                  </button>
                </div>
                {candidates.length > 0 && (
                  <div className="related-links">
                    {candidates.map((candidate) => (
                      <button
                        key={candidate.id}
                        type="button"
                        disabled={formLocked}
                        onClick={() => selectAddress(candidate)}
                      >
                        {candidate.label}
                      </button>
                    ))}
                  </div>
                )}
                {addressError && <small className="field-error">{addressError}</small>}
              </section>

              <section className="residence-picker" aria-labelledby="residence-picker-title">
                <div className="residence-picker__heading">
                  <div>
                    <span className="eyebrow">Ubicación aproximada</span>
                    <h3 id="residence-picker-title">Marca una zona en el mapa</h3>
                  </div>
                  <MapPin size={21} aria-hidden="true" />
                </div>
                <ResidenceMapPicker
                  value={selectedPosition}
                  onChange={(position) => {
                    if (!formLocked) setPin(position);
                  }}
                />
                <div className="residence-picker__status" aria-live="polite">
                  <span>
                    {selectedPosition
                      ? residenceConsent
                        ? "Zona marcada. Al guardar se reducirá a una celda aproximada antes de contribuir al mapa público."
                        : "Zona marcada solo para este formulario. Activa el consentimiento para guardarla de forma agregada."
                      : "Haz clic en el mapa para marcar una ubicación aproximada."}
                  </span>
                  {selectedPosition && (
                    <button
                      className="button button--ghost"
                      type="button"
                      onClick={clearPin}
                      disabled={formLocked}
                    >
                      Quitar pin
                    </button>
                  )}
                </div>
              </section>

              <label>
                <span>Notas privadas</span>
                <textarea
                  rows={3}
                  {...register("notes")}
                  disabled={formLocked}
                  aria-invalid={Boolean(errors.notes)}
                />
                {errors.notes && (
                  <small className="field-error">Usa 2000 caracteres o menos.</small>
                )}
              </label>

              <section className="residence-consent">
                <MapPin size={21} aria-hidden="true" />
                <div>
                  <strong>
                    Residencia y vigilancia comunitaria
                    <RequiredMark />
                  </strong>
                  <p>
                    Si autorizas, la ubicación se agrupa y se desplaza antes de aparecer como una
                    zona pública. Nunca se publica una dirección ni un punto de residencia.
                  </p>
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      name={consentField.name}
                      ref={consentField.ref}
                      onBlur={consentField.onBlur}
                      disabled={formLocked}
                      onChange={(event) => {
                        void consentField.onChange(event);
                        if (event.target.checked) clearErrors("residence_consent");
                        void trigger(["residence_zone_code", "residence_consent"]);
                      }}
                      aria-invalid={Boolean(errors.residence_consent)}
                    />
                    <span>
                      Autorizo el uso anónimo y agregado de los hallazgos de esta mascota.
                    </span>
                  </label>
                  {errors.residence_consent && (
                    <small className="field-error">{errors.residence_consent.message}</small>
                  )}
                </div>
                <ShieldCheck size={20} aria-hidden="true" />
              </section>
            </div>

            <div className="dialog__actions">
              <button className="button button--ghost" type="button" onClick={onClose}>
                Cancelar
              </button>
              <button className="button button--primary" type="submit" disabled={formLocked}>
                {profileExtracting
                  ? "Esperando ficha..."
                  : submitting
                    ? "Guardando..."
                    : pet
                      ? "Guardar cambios"
                      : "Registrar mascota"}
              </button>
            </div>
          </form>
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
