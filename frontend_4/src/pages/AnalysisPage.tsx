import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  FileCheck2,
  FileUp,
  LoaderCircle,
  Plus,
  ScanLine,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../app/AuthContext";
import { api } from "../app/api";
import { useActivePet } from "../app/PetContext";
import { PageHeader } from "../components/PageHeader";
import { PetFormModal, type PetFormSubmission } from "../components/PetFormModal";
import { StatusBadge } from "../components/StatusBadge";
import {
  buildInitialReviewValues,
  type CbcReviewField,
  hasEnoughCoreValues,
  parseReviewValues,
  splitReviewFields,
} from "../domain/analysis";
import { suggestedPetProfileFromMetadata } from "../domain/petProfile";
import type { AnalysisResult, ExtractionResponse } from "../domain/types";

type Step = "upload" | "extracting" | "review" | "analyzing" | "result";
type InputMode = "file" | "manual";

const [leftReviewFields, rightReviewFields] = splitReviewFields();

interface ReviewFieldTableProps {
  fields: CbcReviewField[];
  inputMode: InputMode;
  values: Record<string, string>;
  onValueChange: (key: string, value: string) => void;
}

function ReviewFieldTable({
  fields,
  inputMode,
  values,
  onValueChange,
}: ReviewFieldTableProps): React.JSX.Element {
  return (
    <section
      className="review-table-card"
      aria-label={`Revisión de parámetros de ${fields[0]?.label ?? "hemograma"} a ${fields.at(-1)?.label ?? "resultado"}`}
      // biome-ignore lint/a11y/noNoninteractiveTabindex: Scrollable table regions must be keyboard focusable.
      tabIndex={0}
    >
      <table className="data-table review-table">
        <thead>
          <tr>
            <th>Parámetro</th>
            <th>Unidades</th>
            <th>{inputMode === "manual" ? "Valor" : "Valor detectado"}</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => (
            <tr key={field.key}>
              <th scope="row">
                {field.label}
                {field.required && (
                  <span className="required-mark" title="Campo principal">
                    {" "}
                    (*)
                  </span>
                )}
                <span>{field.key}</span>
              </th>
              <td>{field.unit}</td>
              <td>
                <input
                  aria-label={`Valor de ${field.label}`}
                  inputMode="decimal"
                  type="text"
                  value={values[field.key] ?? ""}
                  onChange={(event) => onValueChange(field.key, event.target.value)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

interface TemporaryResultProps {
  result: AnalysisResult;
  canPersistLater: boolean;
  onReset: () => void;
}

function TemporaryAnalysisResult({
  result,
  canPersistLater,
  onReset,
}: TemporaryResultProps): React.JSX.Element {
  return (
    <div className="temporary-result">
      <section className="result-summary">
        <div className="result-summary__status">
          <span className="result-summary__icon">
            <FileCheck2 size={24} aria-hidden="true" />
          </span>
          <div>
            <p className="eyebrow">Resultado temporal</p>
            <h2>{result.diagnoses[0] ?? "Lectura completada"}</h2>
          </div>
          <StatusBadge tone={result.persisted ? "success" : "neutral"}>
            {result.persisted ? "Guardado" : "No guardado"}
          </StatusBadge>
        </div>
        <p>{result.summary}</p>
        {!result.persisted && (
          <div className="inline-warning">
            <AlertTriangle size={18} aria-hidden="true" />
            <span>
              {canPersistLater
                ? "Este análisis no se guardó porque no fue asociado a una mascota."
                : "Estás en modo invitado. Este análisis no se guardará ni creará historial."}
            </span>
          </div>
        )}
      </section>

      <section className="dashboard-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Hallazgos</p>
            <h2>Qué observó el sistema</h2>
          </div>
        </div>
        <div className="findings-list">
          {result.findings.map((finding) => (
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
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="dashboard-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Valores confirmados</p>
            <h2>Datos usados por el modelo</h2>
          </div>
        </div>
        <section
          className="table-wrap"
          aria-label="Valores confirmados del hemograma temporal"
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
              {result.lab_values.map((value) => (
                <tr key={value.name}>
                  <th scope="row">
                    {value.label}
                    <span>{value.name}</span>
                  </th>
                  <td className="numeric">
                    {value.value} <span>{value.unit}</span>
                  </td>
                  <td>
                    {value.ref_min}-{value.ref_max}
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

      <div className="panel-actions panel-actions--split">
        <button className="button button--ghost" type="button" onClick={onReset}>
          <ChevronLeft size={17} aria-hidden="true" /> Analizar otro hemograma
        </button>
        {!canPersistLater && (
          <Link className="button button--secondary" to="/registro">
            Crear cuenta
          </Link>
        )}
      </div>
    </div>
  );
}

export function AnalysisPage(): React.JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { activePet, activePetId, setActivePetId, refetch: refetchPets } = useActivePet();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [inputMode, setInputMode] = useState<InputMode>("file");
  const [step, setStep] = useState<Step>("upload");
  const [extraction, setExtraction] = useState<ExtractionResponse | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [associatePet, setAssociatePet] = useState(false);
  const [petModalOpen, setPetModalOpen] = useState(false);
  const [error, setError] = useState("");

  const extractMutation = useMutation({
    mutationFn: (selectedFile: File) => api.extract(selectedFile),
  });
  const analyzeMutation = useMutation({ mutationFn: api.analyzeConfirmed });
  const createPetMutation = useMutation({ mutationFn: api.createPet });
  const { data: breeds = [] } = useQuery({ queryKey: ["breeds"], queryFn: api.breeds });
  const suggestedPetProfile = useMemo(
    () => suggestedPetProfileFromMetadata(extraction?.metadata),
    [extraction],
  );

  useEffect(() => {
    setAssociatePet(Boolean(user && activePet));
  }, [activePet, user]);

  async function extract(): Promise<void> {
    if (!file) return;
    setError("");
    setStep("extracting");
    try {
      const result = await extractMutation.mutateAsync(file);
      setExtraction(result);
      setValues(buildInitialReviewValues(result));
      setAnalysisResult(null);
      setStep("review");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible extraer el archivo.");
      setStep("upload");
    }
  }

  async function analyze(): Promise<void> {
    if (!extraction) return;
    const parsed = parseReviewValues(values);
    if (parsed.invalidFields.length > 0) {
      setError(
        `Revisa estos campos porque no son números válidos: ${parsed.invalidFields.join(", ")}.`,
      );
      return;
    }
    if (!hasEnoughCoreValues(parsed.cbc)) {
      setError("Confirma al menos tres valores principales antes de continuar.");
      return;
    }
    setError("");
    setStep("analyzing");
    try {
      const result = await analyzeMutation.mutateAsync({
        cbc: parsed.cbc,
        metadata: extraction.metadata,
        comments: extraction.comments,
        extraction_provider: extraction.extraction_provider,
        extraction_mode: extraction.extraction_mode,
        extraction_warnings: extraction.warnings,
        filename: file?.name ?? "ingreso-manual",
        file_size: file?.size ?? 0,
        pet_id: user && associatePet ? (activePet?.id ?? activePetId) || undefined : undefined,
      });
      if (result.persisted) {
        await queryClient.invalidateQueries({ queryKey: ["history"] });
        await navigate({ to: "/analisis/$analysisId", params: { analysisId: result.id } });
        return;
      }
      setAnalysisResult(result);
      setStep("result");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible analizar los datos.");
      setStep("review");
    }
  }

  function startManualEntry(): void {
    setFile(null);
    const manualExtraction: ExtractionResponse = {
      cbc: {},
      fields: [],
      metadata: { source: "manual" },
      comments: null,
      extraction_provider: "local",
      extraction_mode: "local",
      fallback_used: false,
      warnings: [],
    };
    setValues(buildInitialReviewValues(manualExtraction));
    setExtraction(manualExtraction);
    setAnalysisResult(null);
    setStep("review");
    setError("");
  }

  function reset(): void {
    setFile(null);
    setExtraction(null);
    setValues({});
    setAnalysisResult(null);
    setStep("upload");
    setPetModalOpen(false);
    setError("");
    if (inputRef.current) inputRef.current.value = "";
  }

  async function createPetFromModal({ payload, photo }: PetFormSubmission): Promise<void> {
    setError("");
    try {
      const savedPet = await createPetMutation.mutateAsync(payload);
      if (photo) await api.uploadPetPhoto(savedPet.id, photo);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["pets"] }),
        queryClient.invalidateQueries({ queryKey: ["epidemiology"] }),
      ]);
      await refetchPets();
      setActivePetId(savedPet.id);
      setAssociatePet(true);
      setPetModalOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No fue posible crear la mascota.");
    }
  }

  return (
    <div className="analysis-page page-flow">
      <PageHeader
        eyebrow={`Nuevo hemograma · ${activePet?.name ?? "Sin mascota"}`}
        title="Interpretar un hemograma"
        description="El archivo se extrae primero. Tú confirmas los valores antes de enviarlos al modelo."
      />

      <ol className="stepper" aria-label="Progreso del análisis">
        {[
          ["upload", "Archivo"],
          ["review", "Revisión"],
          ["analyzing", "Resultado"],
        ].map(([key, label], index) => {
          const activeIndex =
            step === "upload" || step === "extracting" ? 0 : step === "review" ? 1 : 2;
          return (
            <li
              key={key}
              data-state={
                index < activeIndex ? "done" : index === activeIndex ? "active" : "pending"
              }
            >
              <span>{index < activeIndex ? <Check size={15} /> : index + 1}</span>
              <strong>{label}</strong>
            </li>
          );
        })}
      </ol>

      <div className="analysis-workspace">
        <section className="analysis-main">
          {step === "upload" && (
            <div className="upload-panel" data-tour="analisis-upload">
              <fieldset className="input-mode-picker">
                <legend className="sr-only">Forma de ingresar los valores</legend>
                <button
                  type="button"
                  data-active={inputMode === "file"}
                  onClick={() => setInputMode("file")}
                >
                  Cargar archivo
                </button>
                <button
                  type="button"
                  data-active={inputMode === "manual"}
                  onClick={() => setInputMode("manual")}
                >
                  Ingreso manual
                </button>
              </fieldset>
              {inputMode === "file" ? (
                <>
                  <input
                    ref={inputRef}
                    className="sr-only"
                    id="hemogram-file"
                    type="file"
                    accept=".pdf,.csv,.xlsx,.xls,.jpg,.jpeg,.png,.tif,.tiff,.webp,application/pdf,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,image/jpeg,image/png,image/tiff,image/webp"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  />
                  <label className="drop-area" htmlFor="hemogram-file">
                    <span className="drop-area__icon">
                      <FileUp size={28} aria-hidden="true" />
                    </span>
                    <strong title={file?.name}>
                      {file ? file.name : "Selecciona el archivo del hemograma"}
                    </strong>
                    <p>
                      Puedes usar un documento, una hoja de cálculo o una imagen del hemograma.
                      HemoVet no procesa radiografías, frotis ni estudios bioquímicos.
                    </p>
                    <span className="button button--secondary">
                      {file ? "Cambiar archivo" : "Elegir archivo"}
                    </span>
                  </label>
                  {file && (
                    <div className="selected-file">
                      <FileCheck2 size={20} aria-hidden="true" />
                      <div>
                        <strong title={file.name}>{file.name}</strong>
                        <span>
                          {Math.max(1, Math.round(file.size / 1024))} KB ·{" "}
                          {file.type || file.name.split(".").at(-1)?.toUpperCase() || "archivo"}
                        </span>
                      </div>
                      <StatusBadge tone="success">Listo</StatusBadge>
                    </div>
                  )}
                  <button
                    className="button button--primary button--full"
                    type="button"
                    onClick={extract}
                    disabled={!file}
                  >
                    Extraer valores <ScanLine size={18} aria-hidden="true" />
                  </button>
                </>
              ) : (
                <div className="manual-entry-intro">
                  <ScanLine size={30} aria-hidden="true" />
                  <h2>Ingresa los valores del hemograma</h2>
                  <p>
                    Transcribe los resultados desde el documento o la imagen original. Podrás
                    revisarlos antes del análisis.
                  </p>
                  <button
                    className="button button--primary"
                    type="button"
                    onClick={startManualEntry}
                  >
                    Comenzar ingreso manual
                  </button>
                </div>
              )}
            </div>
          )}

          {step === "extracting" && (
            <div className="process-state" data-hydrated>
              <LoaderCircle size={34} aria-hidden="true" />
              <h2>Extrayendo los datos del archivo</h2>
              <p>Buscando parámetros, unidades y comentarios del instrumento.</p>
              <div className="progress-track">
                <span />
              </div>
            </div>
          )}

          {step === "review" && extraction && (
            <div className="review-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">
                    {inputMode === "manual" ? "Ingreso manual" : "Revisión humana obligatoria"}
                  </p>
                  <h2>
                    {inputMode === "manual"
                      ? "Ingresa los valores del hemograma"
                      : "Confirma los valores extraídos"}
                  </h2>
                </div>
                <StatusBadge tone="warn">Pendiente</StatusBadge>
              </div>
              <p>
                {inputMode === "manual"
                  ? "Transcribe los valores directamente desde el reporte. Los campos marcados con * cuentan para el mínimo de análisis."
                  : "Compara cada dato con el documento, imagen o fuente original. Puedes corregir cualquier lectura antes del análisis."}
              </p>
              {extraction.warnings.map((warning) => (
                <div className="inline-warning" key={warning}>
                  <AlertTriangle size={18} aria-hidden="true" />
                  <span>{warning}</span>
                </div>
              ))}
              {user && !activePet && (
                <section className="pet-create-prompt" aria-labelledby="pet-create-title">
                  <div>
                    <p className="eyebrow">Mascota para historial</p>
                    <h3 id="pet-create-title">¿Crear una mascota para este hemograma?</h3>
                    <p>
                      Si la registras ahora, este análisis puede guardarse en su historial.
                      {suggestedPetProfile.detectedFields.length > 0
                        ? ` Detectamos: ${suggestedPetProfile.detectedFields.join(", ")}.`
                        : " También puedes subir una imagen de la ficha médica en el formulario."}
                    </p>
                  </div>
                  <button
                    className="button button--secondary"
                    type="button"
                    onClick={() => setPetModalOpen(true)}
                  >
                    <Plus size={17} aria-hidden="true" />
                    Crear mascota
                  </button>
                </section>
              )}
              <div className="review-table-grid">
                <ReviewFieldTable
                  fields={leftReviewFields}
                  inputMode={inputMode}
                  values={values}
                  onValueChange={(key, value) =>
                    setValues((current) => ({ ...current, [key]: value }))
                  }
                />
                <ReviewFieldTable
                  fields={rightReviewFields}
                  inputMode={inputMode}
                  values={values}
                  onValueChange={(key, value) =>
                    setValues((current) => ({ ...current, [key]: value }))
                  }
                />
              </div>
              <div className="panel-actions panel-actions--split">
                <button className="button button--ghost" type="button" onClick={reset}>
                  <ChevronLeft size={17} aria-hidden="true" /> Volver al origen
                </button>
                <button className="button button--primary" type="button" onClick={analyze}>
                  Confirmar y analizar <Check size={17} aria-hidden="true" />
                </button>
              </div>
            </div>
          )}

          {step === "analyzing" && (
            <div className="process-state">
              <LoaderCircle size={34} aria-hidden="true" />
              <h2>Analizando el perfil completo</h2>
              <p>El modelo revisa relaciones entre las series roja, blanca y plaquetaria.</p>
              <div className="progress-track">
                <span />
              </div>
            </div>
          )}

          {step === "result" && analysisResult && (
            <TemporaryAnalysisResult
              result={analysisResult}
              canPersistLater={Boolean(user)}
              onReset={reset}
            />
          )}

          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
        </section>

        <aside className="analysis-aside">
          <section className="context-panel">
            <p className="eyebrow">Contexto actual</p>
            <h2>{user ? (activePet?.name ?? "Análisis sin mascota") : "Modo invitado"}</h2>
            {user && activePet ? (
              <>
                <dl>
                  <div>
                    <dt>Raza</dt>
                    <dd>{activePet.breed}</dd>
                  </div>
                  <div>
                    <dt>Especie admitida</dt>
                    <dd>Canina</dd>
                  </div>
                  <div>
                    <dt>Persistencia</dt>
                    <dd>{associatePet ? "Se guardará en su historial" : "Análisis temporal"}</dd>
                  </div>
                </dl>
                <label className="checkbox-row analysis-association">
                  <input
                    type="checkbox"
                    checked={associatePet}
                    onChange={(event) => setAssociatePet(event.target.checked)}
                  />
                  <span>Asociar este hemograma a {activePet.name} y guardar historial.</span>
                </label>
              </>
            ) : (
              <p className="context-panel__message">
                {user
                  ? "Puedes analizar este hemograma sin asociarlo a una mascota. Para guardar historial personalizado, registra una mascota."
                  : "Estás usando HemoVet en modo invitado. Puedes analizar un hemograma y ver el resultado del modelo, pero tus datos no se guardarán."}
              </p>
            )}
          </section>
          <section className="context-note">
            <AlertTriangle size={19} aria-hidden="true" />
            <div>
              <strong>La calidad del archivo importa</strong>
              <p>Un dato incorrecto puede cambiar la clasificación. Verifica la fuente original.</p>
            </div>
          </section>
        </aside>
      </div>
      <PetFormModal
        open={petModalOpen}
        breeds={breeds}
        initialValues={suggestedPetProfile.values}
        submitting={createPetMutation.isPending}
        onClose={() => setPetModalOpen(false)}
        onSubmit={createPetFromModal}
      />
    </div>
  );
}
