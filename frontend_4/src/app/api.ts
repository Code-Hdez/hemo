import { browserChatSessionId, clearAllChatSessionManifests } from "../domain/chatSession";
import { cleanVisibleAssistantText, type SseEvent, SseParser } from "../domain/chatStream";
import { glossarySlugForFinding } from "../domain/glossary";
import type {
  AnalysisResult,
  BreedDistribution,
  ChatAvailability,
  ChatConversation,
  ChatConversationTurn,
  ChatConversationTurnPage,
  ChatErrorEnvelope,
  ChatRequestPayload,
  ChatResponse,
  ChatTurnStatus,
  EpidemiologyPoint,
  ExtractionResponse,
  LabelActivation,
  ModelQuality,
  NearbyVeterinaryCareRequest,
  NearbyVeterinaryCareResponse,
  OnboardingTourStatus,
  Pet,
  PetInput,
  PetProfileExtraction,
  ResidenceCandidate,
  ResidenceZone,
  SurveillanceReport,
  TemporalAnalytics,
  User,
} from "../domain/types";

const API = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");
const TOKEN_KEY = "hemovet4-token";
// The backend emits a heartbeat every 15 s while it generates, so ~2.5 missed
// heartbeats mean the connection died silently instead of being merely slow.
const SSE_STALL_TIMEOUT_MS = 40_000;

let onUnauthorized: (() => void) | undefined;

interface ApiRequestInit extends RequestInit {
  skipAuth?: boolean;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function chatErrorEnvelope(caught: unknown): ChatErrorEnvelope | undefined {
  if (!(caught instanceof ApiError) || !isRecord(caught.detail)) return undefined;
  const detail = caught.detail;
  if (
    typeof detail.code !== "string" ||
    typeof detail.message !== "string" ||
    typeof detail.retryable !== "boolean" ||
    typeof detail.recovery_action !== "string"
  ) {
    return undefined;
  }
  return {
    code: detail.code,
    message: detail.message,
    detail: typeof detail.detail === "string" ? detail.detail : detail.message,
    category:
      typeof detail.category === "string"
        ? (detail.category as ChatErrorEnvelope["category"])
        : "unexpected",
    retryable: detail.retryable,
    recovery_action: detail.recovery_action as ChatErrorEnvelope["recovery_action"],
    request_id: typeof detail.request_id === "string" ? detail.request_id : "unknown",
    client_message_id:
      typeof detail.client_message_id === "string" ? detail.client_message_id : "unknown",
    conversation_id:
      typeof detail.conversation_id === "string" ? detail.conversation_id : undefined,
    turn_id: typeof detail.turn_id === "string" ? detail.turn_id : undefined,
    attempt: typeof detail.attempt === "number" ? detail.attempt : undefined,
    retry_after_ms: typeof detail.retry_after_ms === "number" ? detail.retry_after_ms : undefined,
    http_status: typeof detail.http_status === "number" ? detail.http_status : 0,
  };
}

export function setUnauthorizedHandler(handler?: () => void): void {
  onUnauthorized = handler;
}

function token(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

type UnauthorizedSource = "session-check" | "login" | "api-request" | "chat-stream";
type SessionState = "valid" | "invalid" | "unknown";

function invalidateSession(activeToken: string | null): void {
  if (activeToken) localStorage.removeItem(TOKEN_KEY);
  clearAllChatSessionManifests();
  onUnauthorized?.();
}

async function revalidateSession(activeToken: string | null): Promise<SessionState> {
  const headers = new Headers();
  if (activeToken) headers.set("Authorization", `Bearer ${activeToken}`);
  try {
    const response = await fetch(`${API}/auth/me`, { headers, credentials: "include" });
    if (response.ok) return "valid";
    return response.status === 401 ? "invalid" : "unknown";
  } catch {
    return "unknown";
  }
}

async function handleUnauthorized(
  source: UnauthorizedSource,
  activeToken: string | null,
): Promise<boolean> {
  if (source === "login") return false;
  if (source === "session-check") {
    invalidateSession(activeToken);
    return true;
  }
  const state = await revalidateSession(activeToken);
  if (state !== "invalid") return false;
  invalidateSession(activeToken);
  return true;
}

function errorMessage(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    return (
      detail
        .map((item) =>
          typeof item === "object" && item ? String((item as { msg?: unknown }).msg ?? "") : "",
        )
        .filter(Boolean)
        .join(" ") || "Revisa los datos enviados."
    );
  }
  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return "No fue posible completar la acción.";
}

function publicMediaUrl(photoUrl: string | null | undefined): string | undefined {
  if (!photoUrl) return undefined;
  if (/^https?:\/\//i.test(photoUrl) || photoUrl.startsWith("data:")) return photoUrl;
  try {
    const apiOrigin = new URL(API, window.location.origin).origin;
    return new URL(photoUrl, apiOrigin).toString();
  } catch {
    return photoUrl;
  }
}

export function mapPet(pet: Pet): Pet {
  return {
    ...pet,
    image: publicMediaUrl(pet.photo_url) ?? pet.image,
    residence_consent: Boolean(pet.residence_consent),
  };
}

export function mapAnalysis(analysis: AnalysisResult): AnalysisResult {
  return {
    ...analysis,
    imputed_fields: analysis.imputed_fields ?? [],
    extraction_warnings: analysis.extraction_warnings ?? [],
    diagnoses: analysis.diagnoses ?? [],
    qc_flags: analysis.qc_flags ?? [],
    lab_values: analysis.lab_values ?? [],
    findings: (analysis.findings ?? []).map((finding) => ({
      ...finding,
      glossary_slug: finding.glossary_slug ?? glossarySlugForFinding(finding.label),
    })),
    persisted: Boolean(analysis.persisted),
  };
}

async function request<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { skipAuth = false, ...fetchInit } = init;
  const headers = new Headers(init.headers);
  const activeToken = skipAuth ? null : token();
  if (!skipAuth && activeToken) headers.set("Authorization", `Bearer ${activeToken}`);
  if (!skipAuth && (path === "/chat" || path.startsWith("/chat/"))) {
    headers.set("X-HemoVet-Browser-Session-ID", browserChatSessionId());
  }
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API}${path}`, {
      ...fetchInit,
      headers,
      credentials: skipAuth ? "omit" : "include",
    });
  } catch {
    throw new ApiError(
      "No fue posible conectar con HemoVet. Verifica que el backend esté disponible.",
    );
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const detail = (payload as { detail?: unknown }).detail;
    if (response.status === 401) {
      const source: UnauthorizedSource =
        path === "/auth/login" ? "login" : path === "/auth/me" ? "session-check" : "api-request";
      await handleUnauthorized(source, activeToken);
    }
    throw new ApiError(errorMessage(detail), response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

interface StreamChatOptions {
  signal?: AbortSignal;
  onEvent: (event: SseEvent) => void;
}

type WireChatPayload = Omit<ChatRequestPayload, "context_scope"> & {
  context_scope: ChatRequestPayload["context_scope"] | "uploaded_analysis" | "historical_analysis";
};

async function streamChatOnce(
  payload: WireChatPayload,
  options: StreamChatOptions,
): Promise<ChatResponse> {
  const headers = new Headers({
    Accept: "text/event-stream",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
  });
  const activeToken = token();
  if (activeToken) headers.set("Authorization", `Bearer ${activeToken}`);
  headers.set("X-HemoVet-Browser-Session-ID", browserChatSessionId());
  let response: Response;
  try {
    response = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
      credentials: "include",
      signal: options.signal,
    });
  } catch (caught) {
    if (caught instanceof DOMException && caught.name === "AbortError") throw caught;
    throw new ApiError("No fue posible conectar con el asistente.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = (body as { detail?: unknown }).detail;
    if (response.status === 401) {
      const expired = await handleUnauthorized("chat-stream", activeToken);
      throw new ApiError(
        expired ? "Tu sesión parece haber expirado." : "No se pudo autenticar el stream del chat.",
        response.status,
        detail,
      );
    }
    throw new ApiError(errorMessage(detail), response.status, detail);
  }
  if (!response.body) throw new ApiError("El servidor no inició el flujo de respuesta.");
  const contentType = response.headers.get("Content-Type")?.toLowerCase() ?? "";
  const responseRequestId = response.headers.get("X-Request-ID") ?? undefined;
  const serverRequestId = responseRequestId ?? crypto.randomUUID();
  if (!contentType.startsWith("text/event-stream")) {
    throw new ApiError("El servidor no devolvió un flujo SSE válido.", undefined, {
      code: "stream_content_type",
      content_type: contentType || null,
    });
  }

  const parser = new SseParser();
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let finalResponse: ChatResponse | undefined;
  let knownConversationId = payload.conversation_id ?? undefined;
  let knownRequestId = responseRequestId;
  let knownTurnId: string | undefined;
  let knownAttempt: number | undefined;
  let lastEventSequence: number | undefined;
  let lastEventFingerprint: string | undefined;
  let reachedEof = false;
  let aborted = options.signal?.aborted ?? false;
  let cancellation: Promise<void> | undefined;
  const abortError = () => new DOMException("Aborted", "AbortError");
  const transportEnvelope = (code: string, message: string, detail: string): ChatErrorEnvelope => ({
    code,
    message,
    detail,
    category: "transport",
    retryable: true,
    recovery_action: knownConversationId ? "poll_turn" : "retry_same_turn",
    request_id: knownRequestId ?? serverRequestId,
    client_message_id: payload.client_message_id,
    conversation_id: knownConversationId,
    turn_id: knownTurnId,
    attempt: knownAttempt,
    http_status: 0,
  });
  // Every chunk restarts the watchdog, so the heartbeat keeps a slow but live
  // turn open while a connection that stopped speaking is reported instead of
  // leaving the composer waiting forever.
  const readWithWatchdog = async (): Promise<Awaited<ReturnType<typeof reader.read>>> => {
    let watchdog = 0;
    const stall = new Promise<never>((_resolve, reject) => {
      watchdog = window.setTimeout(() => {
        const envelope = transportEnvelope(
          "sse_stalled",
          "El asistente dejó de responder durante la generación.",
          "Consulta el estado del turno; puede seguir procesándose en el servidor.",
        );
        reject(new ApiError(envelope.message, undefined, envelope));
      }, SSE_STALL_TIMEOUT_MS);
    });
    try {
      return await Promise.race([reader.read(), stall]);
    } finally {
      window.clearTimeout(watchdog);
    }
  };
  const onAbort = () => {
    aborted = true;
    cancellation = reader.cancel(abortError()).catch(() => undefined);
  };
  options.signal?.addEventListener("abort", onAbort, { once: true });

  const processEvents = (events: SseEvent[]) => {
    for (const rawEvent of events) {
      if (finalResponse) {
        throw streamProtocolError(
          "stream_event_after_done",
          "El asistente envió datos después del evento final.",
        );
      }
      let publicEvent = cleanChatStreamEvent(rawEvent);
      if (publicEvent.event === "start") {
        publicEvent = normalizeContextEvent(publicEvent);
      }
      const identity = streamEventIdentity(publicEvent.data);
      if (
        identity.conversationId &&
        knownConversationId &&
        identity.conversationId !== knownConversationId
      ) {
        throw streamProtocolError(
          "stream_conversation_mismatch",
          "El flujo no pertenece a la conversación solicitada.",
        );
      }
      if (identity.clientMessageId && identity.clientMessageId !== payload.client_message_id) {
        throw streamProtocolError(
          "stream_client_message_mismatch",
          "El flujo no pertenece al turno solicitado.",
        );
      }
      if (identity.requestId && knownRequestId && identity.requestId !== knownRequestId) {
        throw streamProtocolError(
          "stream_request_mismatch",
          "El flujo cambió de solicitud durante la respuesta.",
        );
      }
      if (identity.turnId && knownTurnId && identity.turnId !== knownTurnId) {
        throw streamProtocolError(
          "stream_turn_mismatch",
          "El flujo cambió de turno durante la respuesta.",
        );
      }
      if (
        identity.attempt !== undefined &&
        knownAttempt !== undefined &&
        identity.attempt !== knownAttempt
      ) {
        throw streamProtocolError(
          "stream_attempt_mismatch",
          "El flujo cambió de intento durante la respuesta.",
        );
      }
      knownConversationId = identity.conversationId ?? knownConversationId;
      knownRequestId = identity.requestId ?? knownRequestId;
      knownTurnId = identity.turnId ?? knownTurnId;
      knownAttempt = identity.attempt ?? knownAttempt;

      const sequence = streamEventSequence(publicEvent.data);
      if (sequence !== undefined) {
        const fingerprint = `${publicEvent.event}:${JSON.stringify(publicEvent.data)}`;
        if (lastEventSequence === sequence) {
          if (lastEventFingerprint === fingerprint) continue;
          throw streamProtocolError(
            "stream_sequence_conflict",
            "El asistente envió dos eventos diferentes con la misma secuencia.",
          );
        }
        if (lastEventSequence !== undefined && sequence !== lastEventSequence + 1) {
          throw streamProtocolError(
            sequence < lastEventSequence ? "stream_event_out_of_order" : "stream_sequence_gap",
            sequence < lastEventSequence
              ? "Los eventos del asistente llegaron fuera de orden."
              : "Falta un evento intermedio en el flujo del asistente.",
          );
        }
        lastEventSequence = sequence;
        lastEventFingerprint = fingerprint;
      }
      if (publicEvent.event === "done") {
        const candidate = publicEvent.data;
        if (!isChatResponse(candidate)) {
          throw streamProtocolError(
            "stream_done_invalid",
            "El evento final del asistente está incompleto.",
          );
        }
        if (knownConversationId && candidate.conversation_id !== knownConversationId) {
          throw streamProtocolError(
            "stream_conversation_mismatch",
            "La respuesta final no pertenece a la conversación solicitada.",
          );
        }
        knownConversationId = candidate.conversation_id;
        finalResponse = candidate;
      }
      options.onEvent(publicEvent);
      if (rawEvent.event === "error") {
        const errorData = rawEvent.data as { message?: unknown; http_status?: unknown };
        const message =
          typeof errorData.message === "string"
            ? errorData.message
            : "El asistente no pudo completar la respuesta.";
        const httpStatus =
          typeof errorData.http_status === "number" ? errorData.http_status : undefined;
        throw new ApiError(message, httpStatus, rawEvent.data);
      }
    }
  };

  try {
    if (aborted) throw abortError();
    while (!finalResponse) {
      const { done, value } = await readWithWatchdog();
      if (aborted) throw abortError();
      if (done) {
        reachedEof = true;
        processEvents(parseStreamEvents(parser, decoder.decode(), true));
        break;
      }
      processEvents(parseStreamEvents(parser, decoder.decode(value, { stream: true }), false));
    }
  } catch (caught) {
    if (aborted && !(caught instanceof DOMException && caught.name === "AbortError")) {
      throw abortError();
    }
    throw caught;
  } finally {
    options.signal?.removeEventListener("abort", onAbort);
    if (cancellation) {
      await cancellation;
    } else if (!reachedEof) {
      await reader.cancel().catch(() => undefined);
    }
    reader.releaseLock();
  }
  if (aborted) throw abortError();
  if (!finalResponse) {
    const envelope = transportEnvelope(
      "sse_connection_interrupted",
      "La conexión con el asistente se interrumpió antes de confirmar la respuesta.",
      "Consulta el estado del turno; si quedó interrumpido podrás reintentarlo.",
    );
    throw new ApiError(envelope.message, undefined, envelope);
  }
  return finalResponse;
}

function parseStreamEvents(parser: SseParser, decoded: string, finish: boolean): SseEvent[] {
  try {
    const events = parser.push(decoded);
    return finish ? [...events, ...parser.finish()] : events;
  } catch (caught) {
    throw new ApiError("El asistente envió un evento de stream inválido.", undefined, {
      code: "stream_parse_error",
      cause: caught instanceof Error ? caught.message : String(caught),
    });
  }
}

function streamProtocolError(code: string, message: string): ApiError {
  return new ApiError(message, undefined, { code });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isChatResponse(value: unknown): value is ChatResponse {
  if (!isRecord(value) || !isRecord(value.usage)) return false;
  const validScope = new Set([
    "general",
    "selected_hemogram",
    "hemogram_history",
    "uploaded_analysis",
    "historical_analysis",
  ]);
  const validOrigin = new Set(["llm", "legacy"]);
  const validStreamMode = new Set(["live_validated", "buffered_validated"]);
  const origin = typeof value.response_origin === "string" ? value.response_origin : undefined;
  const generativeOriginIsConsistent =
    origin !== "llm" ||
    (value.llm_invoked === true &&
      typeof value.model === "string" &&
      value.model.length > 0 &&
      typeof value.generation_attempts === "number" &&
      value.generation_attempts >= 1);
  return (
    typeof value.conversation_id === "string" &&
    value.conversation_id.length > 0 &&
    typeof value.message_id === "string" &&
    value.message_id.length > 0 &&
    typeof value.answer === "string" &&
    value.answer.trim().length > 0 &&
    typeof value.scope === "string" &&
    validScope.has(value.scope) &&
    Array.isArray(value.case_facts) &&
    value.case_facts.every(
      (fact) =>
        isRecord(fact) && typeof fact.parameter === "string" && typeof fact.value === "string",
    ) &&
    Array.isArray(value.sources) &&
    value.sources.every(isRecord) &&
    Array.isArray(value.warnings) &&
    value.warnings.every((warning) => typeof warning === "string") &&
    typeof value.safety_action === "string" &&
    "model" in value &&
    (typeof value.model === "string" || value.model === null) &&
    typeof value.usage.prompt_tokens === "number" &&
    Number.isInteger(value.usage.prompt_tokens) &&
    value.usage.prompt_tokens >= 0 &&
    typeof value.usage.completion_tokens === "number" &&
    Number.isInteger(value.usage.completion_tokens) &&
    value.usage.completion_tokens >= 0 &&
    typeof value.duration_ms === "number" &&
    Number.isFinite(value.duration_ms) &&
    typeof value.finish_reason === "string" &&
    typeof value.llm_invoked === "boolean" &&
    typeof value.response_origin === "string" &&
    validOrigin.has(value.response_origin) &&
    generativeOriginIsConsistent &&
    typeof value.attempt === "number" &&
    Number.isInteger(value.attempt) &&
    value.attempt >= 1 &&
    typeof value.generation_attempts === "number" &&
    Number.isInteger(value.generation_attempts) &&
    value.generation_attempts >= 0 &&
    typeof value.stream_mode === "string" &&
    validStreamMode.has(value.stream_mode) &&
    typeof value.validation_status === "string"
  );
}

function streamConversationId(data: unknown): string | undefined {
  if (!isRecord(data)) return undefined;
  if (typeof data.conversation_id === "string" && data.conversation_id) {
    return data.conversation_id;
  }
  return isRecord(data.context) && typeof data.context.conversation_id === "string"
    ? data.context.conversation_id
    : undefined;
}

function streamContextRevision(data: unknown): number | undefined {
  if (!isRecord(data)) return undefined;
  const direct = data.context_revision ?? data.revision;
  if (typeof direct === "number" && Number.isInteger(direct)) return direct;
  if (!isRecord(data.context)) return undefined;
  const nested = data.context.context_revision ?? data.context.revision;
  return typeof nested === "number" && Number.isInteger(nested) ? nested : undefined;
}

function streamEventIdentity(data: unknown): {
  requestId?: string;
  conversationId?: string;
  turnId?: string;
  clientMessageId?: string;
  attempt?: number;
} {
  if (!isRecord(data)) return {};
  const nested = isRecord(data.context) ? data.context : undefined;
  const stringValue = (name: string): string | undefined => {
    const direct = data[name];
    if (typeof direct === "string" && direct) return direct;
    const contextual = nested?.[name];
    return typeof contextual === "string" && contextual ? contextual : undefined;
  };
  const attempt = data.attempt ?? nested?.attempt;
  return {
    requestId: stringValue("request_id"),
    conversationId: stringValue("conversation_id"),
    turnId: stringValue("turn_id"),
    clientMessageId: stringValue("client_message_id"),
    attempt: typeof attempt === "number" && Number.isInteger(attempt) ? attempt : undefined,
  };
}

function normalizeContextEvent(event: SseEvent): SseEvent {
  if (!isRecord(event.data)) return event;
  const conversationId = streamConversationId(event.data);
  const contextRevision = streamContextRevision(event.data);
  return {
    ...event,
    data: {
      ...event.data,
      ...(conversationId ? { conversation_id: conversationId } : {}),
      ...(contextRevision !== undefined ? { context_revision: contextRevision } : {}),
    },
  };
}

function streamEventSequence(data: unknown): number | undefined {
  if (!isRecord(data)) return undefined;
  const candidate = data.sequence ?? data.seq ?? data.index;
  return typeof candidate === "number" && Number.isInteger(candidate) ? candidate : undefined;
}

async function streamChat(
  payload: ChatRequestPayload,
  options: StreamChatOptions,
): Promise<ChatResponse> {
  const preferred: WireChatPayload =
    payload.context_scope === "hemogram_history" ? { ...payload, analysis_id: undefined } : payload;
  try {
    return await streamChatOnce(preferred, options);
  } catch (caught) {
    if (!(caught instanceof ApiError) || caught.status !== 422) throw caught;
    // Only a legacy server rejects the canonical scope with an untyped 422.
    // A typed envelope (context_budget_exceeded, …) is a real verdict about the
    // turn: resending it would fail the same way after occupying the single
    // generation slot a second time.
    if (chatErrorEnvelope(caught)) throw caught;
    if (payload.context_scope === "selected_hemogram" && payload.analysis_id) {
      return streamChatOnce({ ...payload, context_scope: "uploaded_analysis" }, options);
    }
    if (payload.context_scope === "hemogram_history" && payload.analysis_id) {
      return streamChatOnce(
        { ...payload, context_scope: "historical_analysis", pet_id: undefined },
        options,
      );
    }
    throw caught;
  }
}

function cleanChatStreamEvent(event: SseEvent): SseEvent {
  if (
    (event.event === "final" || event.event === "done") &&
    typeof event.data === "object" &&
    event.data !== null &&
    "answer" in event.data &&
    typeof event.data.answer === "string"
  ) {
    return {
      ...event,
      data: { ...event.data, answer: cleanVisibleAssistantText(event.data.answer) },
    };
  }
  return event;
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [name, value] of Object.entries(params)) {
    if (value !== undefined) search.set(name, String(value));
  }
  const value = search.toString();
  return value ? `?${value}` : "";
}

export const api = {
  login: (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    return request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
  },
  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      clearAllChatSessionManifests();
    }
  },
  register: (payload: { full_name: string; email: string; password: string }) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<User>("/auth/me"),
  updateOnboardingTour: (payload: {
    status: Exclude<OnboardingTourStatus, "pending">;
    version: string;
  }) =>
    request<User>("/auth/me/onboarding-tour", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  pets: async () => (await request<Pet[]>("/pets")).map(mapPet),
  pet: async (id: string) => mapPet(await request<Pet>(`/pets/${encodeURIComponent(id)}`)),
  createPet: async (payload: PetInput) =>
    mapPet(await request<Pet>("/pets", { method: "POST", body: JSON.stringify(payload) })),
  updatePet: async (id: string, payload: PetInput) =>
    mapPet(
      await request<Pet>(`/pets/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    ),
  uploadPetPhoto: async (id: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return mapPet(
      await request<Pet>(`/pets/${encodeURIComponent(id)}/photo`, {
        method: "POST",
        body,
      }),
    );
  },
  deletePetPhoto: async (id: string) =>
    mapPet(
      await request<Pet>(`/pets/${encodeURIComponent(id)}/photo`, {
        method: "DELETE",
      }),
    ),
  deletePet: (id: string) => request<void>(`/pets/${encodeURIComponent(id)}`, { method: "DELETE" }),
  extractPetProfile: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<PetProfileExtraction>("/pets/extract-profile", {
      method: "POST",
      body,
    });
  },
  breeds: () => request<string[]>("/breeds"),
  residenceZones: () => request<ResidenceZone[]>("/residence/zones"),
  resolveResidence: (queryText: string, limit = 5) =>
    request<ResidenceCandidate[]>("/residence/resolve", {
      method: "POST",
      body: JSON.stringify({ query: queryText, limit }),
    }),
  nearbyVeterinaryCare: (payload: NearbyVeterinaryCareRequest) =>
    request<NearbyVeterinaryCareResponse>("/residence/nearby-veterinary-care", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  extract: (file: File, extractionMode: "auto" | "gemini" | "local" = "auto") => {
    const body = new FormData();
    body.append("file", file);
    return request<ExtractionResponse>(`/extract${query({ extraction_mode: extractionMode })}`, {
      method: "POST",
      body,
      skipAuth: true,
    });
  },
  analyzeConfirmed: async (payload: {
    cbc: Record<string, number>;
    metadata: Record<string, string | null>;
    comments: string | null;
    extraction_provider: ExtractionResponse["extraction_provider"];
    extraction_mode: ExtractionResponse["extraction_mode"];
    extraction_warnings: string[];
    filename: string;
    file_size: number;
    pet_id?: string;
  }) =>
    mapAnalysis(
      await request<AnalysisResult>("/analyze/confirmed", {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: !payload.pet_id,
      }),
    ),
  history: async (options: { petId?: string; limit?: number; offset?: number } = {}) => {
    const fetchPage = (limit?: number, offset?: number) =>
      request<AnalysisResult[]>(`/history${query({ pet_id: options.petId, limit, offset })}`);
    if (options.limit !== undefined || options.offset !== undefined) {
      return (await fetchPage(options.limit, options.offset)).map(mapAnalysis);
    }

    const pageSize = 200;
    const all: AnalysisResult[] = [];
    const seen = new Set<string>();
    for (let offset = 0; ; offset += pageSize) {
      const page = await fetchPage(pageSize, offset);
      let added = 0;
      for (const analysis of page) {
        if (seen.has(analysis.id)) continue;
        seen.add(analysis.id);
        all.push(mapAnalysis(analysis));
        added += 1;
      }
      if (page.length < pageSize) break;
      if (added === 0) {
        throw new ApiError("El historial devolvió una paginación inconsistente.", undefined, {
          code: "history_pagination_stalled",
          offset,
        });
      }
    }
    return all;
  },
  analysis: async (id: string) =>
    mapAnalysis(await request<AnalysisResult>(`/analysis/${encodeURIComponent(id)}`)),

  epidemiology: (periodDays: number, finding?: string) =>
    request<EpidemiologyPoint[]>(
      `/epidemiology/points${query({ period_days: periodDays, finding })}`,
    ),
  epidemiologyStreamUrl: () => `${API}/epidemiology/stream`,
  surveillanceReport: (periodDays: number) =>
    request<SurveillanceReport>(`/surveillance/report${query({ period_days: periodDays })}`),
  temporalAnalytics: (periodDays: number, granularity: "week" | "month" = "week") =>
    request<TemporalAnalytics>(
      `/analytics/temporal${query({ period_days: periodDays, granularity })}`,
    ),
  modelQuality: () => request<ModelQuality>("/model/quality"),
  labelActivation: () => request<LabelActivation>("/analytics/label-activation"),
  breedDistribution: (periodDays = 30) =>
    request<BreedDistribution>(
      `/analytics/breed-distribution${query({ period_days: periodDays })}`,
    ),

  chat: (payload: ChatRequestPayload) =>
    request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify(payload) }),
  chatAvailability: () => request<ChatAvailability>("/chat/health"),
  listChatConversations: async () => {
    try {
      const page = await request<{ items: ChatConversation[] }>("/chat/conversations");
      return page.items ?? [];
    } catch (caught) {
      if (
        caught instanceof ApiError &&
        (caught.status === 404 || caught.status === 405 || caught.status === 501)
      ) {
        return [];
      }
      throw caught;
    }
  },
  createChatConversation: async (
    payload: Pick<ChatRequestPayload, "context_scope" | "analysis_id" | "pet_id">,
  ) => {
    try {
      return await request<ChatConversation>("/chat/conversations", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    } catch (caught) {
      if (
        caught instanceof ApiError &&
        (caught.status === 404 || caught.status === 405 || caught.status === 501)
      ) {
        return undefined;
      }
      throw caught;
    }
  },
  clearChatConversation: async (conversationId: string) => {
    try {
      await request<void>(`/chat/conversations/${encodeURIComponent(conversationId)}`, {
        method: "DELETE",
      });
      return true;
    } catch (caught) {
      if (
        caught instanceof ApiError &&
        (caught.status === 404 || caught.status === 405 || caught.status === 501)
      ) {
        return false;
      }
      throw caught;
    }
  },
  chatTurnStatus: (conversationId: string, clientMessageId: string) =>
    request<ChatTurnStatus>(
      `/chat/conversations/${encodeURIComponent(conversationId)}/turns/${encodeURIComponent(clientMessageId)}`,
    ),
  chatConversationTurns: async (conversationId: string) => {
    const items: ChatConversationTurn[] = [];
    const limit = 100;
    for (let offset = 0; offset < 1000; offset += limit) {
      const page = await request<ChatConversationTurnPage>(
        `/chat/conversations/${encodeURIComponent(conversationId)}/turns${query({ limit, offset })}`,
      );
      items.push(...page.items);
      if (page.items.length < limit) break;
    }
    return items;
  },
  cancelChatTurn: (conversationId: string, clientMessageId: string, attempt: number) =>
    request<ChatTurnStatus>(
      `/chat/conversations/${encodeURIComponent(conversationId)}/turns/${encodeURIComponent(clientMessageId)}/cancel`,
      { method: "POST", body: JSON.stringify({ attempt }) },
    ),
  streamChat,
};
