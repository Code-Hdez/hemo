import type { AnalysisResult, ChatScope, ChatSource, Pet } from "./types";

const unsafeMedicalRequest =
  /(dosis|medicamento|paracetamol|tratamiento|diagn[oó]stico|tiene ehrlichia)/i;

const technicalSourcePattern =
  /(?:_pdf(?:_|$)|_pages?_\d|docling|knowledge_base|\.(?:pdf|md|json|epub)$|[/\\])/i;

export interface VisibleChatSource {
  key: string;
  title: string;
  details: string[];
}

export function isUnsafeMedicalRequest(message: string): boolean {
  return unsafeMedicalRequest.test(message);
}

function safeSourceText(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const cleaned = value.replace(/\0/g, "").replace(/\s+/g, " ").trim();
  if (
    !cleaned ||
    ["unknown", "none", "null", "nan"].includes(cleaned.toLowerCase()) ||
    technicalSourcePattern.test(cleaned)
  ) {
    return undefined;
  }
  return cleaned.slice(0, 260);
}

function safePage(value: unknown): number | undefined {
  return typeof value === "number" && Number.isInteger(value) && value > 0 ? value : undefined;
}

/**
 * Projects citation DTOs to display-only data. Technical IDs, paths and scores
 * are intentionally absent from the return type and are never used as labels.
 */
export function visibleChatSources(sources: ChatSource[]): VisibleChatSource[] {
  const visible: VisibleChatSource[] = [];
  const seen = new Set<string>();

  sources.forEach((source, index) => {
    const title =
      safeSourceText(source.display_title) ??
      safeSourceText(source.title) ??
      "Fuente veterinaria consultada";
    const edition = safeSourceText(source.edition);
    const displayTitle =
      edition && !title.toLowerCase().includes(edition.toLowerCase())
        ? `${title}, ${edition}`
        : title;
    const chapter = safeSourceText(source.chapter);
    const section = safeSourceText(source.section) ?? safeSourceText(source.heading_path);
    const pageStart = safePage(source.page_start);
    const pageEnd = safePage(source.page_end);
    const authors = Array.isArray(source.authors)
      ? source.authors.flatMap((author) => safeSourceText(author) ?? [])
      : [];
    const details = [
      authors.length > 0 ? `Autoría: ${authors.join(", ")}` : undefined,
      chapter ? `Capítulo: ${chapter}` : undefined,
      section && section.toLowerCase() !== chapter?.toLowerCase()
        ? `Sección: ${section}`
        : undefined,
      pageStart
        ? pageEnd && pageEnd >= pageStart && pageEnd !== pageStart
          ? `Páginas: ${pageStart}–${pageEnd}`
          : `Página: ${pageStart}`
        : undefined,
      safeSourceText(source.reference),
    ].filter((detail): detail is string => Boolean(detail));

    if (details.length === 0) {
      details.push("Referencia bibliográfica disponible en el corpus de HemoVet.");
    }
    const fingerprint = `${displayTitle}\0${details.join("\0")}`;
    if (seen.has(fingerprint)) return;
    seen.add(fingerprint);
    visible.push({ key: `citation-${index}`, title: displayTitle, details });
  });

  return visible;
}

export function formatAssistantContext(
  scope: ChatScope,
  pet: Pet | null,
  analysis: AnalysisResult | undefined,
  historyCount: number,
): { short: string; detail: string } {
  if (scope === "general") {
    return {
      short: "Chat general",
      detail: "Sin datos clínicos activos. El asistente responderá preguntas generales.",
    };
  }

  const petName = pet?.name ?? "Mascota";
  if (scope === "hemogram_history") {
    return {
      short: `Historial de ${petName}`,
      detail: `${historyCount} ${historyCount === 1 ? "hemograma disponible" : "hemogramas disponibles"} para comparar.`,
    };
  }

  if (!analysis) {
    return {
      short: `Hemograma de ${petName}`,
      detail: "Selecciona un estudio para activar este contexto.",
    };
  }
  const date = new Date(analysis.created_at);
  const dateText = Number.isNaN(date.getTime())
    ? "fecha no disponible"
    : date.toLocaleDateString("es-DO", { day: "numeric", month: "long", year: "numeric" });
  return {
    short: `Hemograma de ${petName}`,
    detail: `Estás viendo el hemograma de ${petName} del ${dateText}.`,
  };
}

export function chatContextKey(
  scope: ChatScope,
  petId: string | undefined,
  analysisId: string | undefined,
): string {
  if (scope === "general") return "general";
  if (scope === "hemogram_history") return `history:${petId ?? "none"}`;
  return `analysis:${petId ?? "none"}:${analysisId ?? "none"}`;
}
