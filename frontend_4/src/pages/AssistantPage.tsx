import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  Bot,
  Check,
  Eraser,
  History,
  LoaderCircle,
  MessageCircle,
  Plus,
  RefreshCw,
  Send,
  ShieldAlert,
  Square,
  User,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../app/AuthContext";
import { ApiError, api, chatErrorEnvelope } from "../app/api";
import { useActivePet } from "../app/PetContext";
import { PageHeader } from "../components/PageHeader";
import { PrivateFeatureGate } from "../components/PrivateFeatureGate";
import { StatusBadge } from "../components/StatusBadge";
import { chatContextKey, formatAssistantContext, visibleChatSources } from "../domain/chat";
import {
  clearChatSessionManifest,
  loadChatSessionManifest,
  saveChatSessionManifest,
} from "../domain/chatSession";
import type {
  ChatAvailability,
  ChatConversation,
  ChatConversationTurn,
  ChatRecoveryAction,
  ChatResponse,
  ChatScope,
  ChatTurnState,
} from "../domain/types";

interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
  clientMessageId?: string;
  status?: string;
}

interface RetryAttempt {
  clientMessageId: string;
  userMessageId: string;
  text: string;
}

interface ErrorState {
  message: string;
  retryable: boolean;
  code?: string;
  recoveryAction: ChatRecoveryAction;
  tone?: "error" | "status";
  retryAfterMs?: number;
}

interface ActiveRequest {
  id: string;
  assistantMessageId: string;
  clientMessageId: string;
  controller: AbortController;
  reason?: "context-change" | "new-chat" | "clear" | "stop" | "unmount";
  conversationId?: string;
  attempt?: number;
  retryAttempt: RetryAttempt;
}

const suggestionsByScope: Record<ChatScope, string[]> = {
  general: [
    "¿Qué mide un hemograma canino?",
    "¿Qué diferencia hay entre eritrocitos y leucocitos?",
    "¿Qué información puede aportar el hematocrito?",
  ],
  selected_hemogram: [
    "¿Qué valores aparecen fuera del rango?",
    "Explícame el valor de los leucocitos.",
    "¿Se observa algún patrón hematológico que deba consultar?",
    "¿Qué preguntas puedo hacerle a mi veterinario sobre este hemograma?",
  ],
  hemogram_history: [
    "¿Qué cambió entre los estudios?",
    "¿Qué parámetros muestran una tendencia?",
    "Compara los leucocitos a través del tiempo.",
    "¿Qué preguntas puedo hacerle a mi veterinario sobre estos cambios?",
  ],
};

const configuredMessageLimit = Number(import.meta.env.VITE_CHAT_MESSAGE_MAX_CHARS ?? "2000");
const CHAT_MESSAGE_MAX_CHARS =
  Number.isFinite(configuredMessageLimit) && configuredMessageLimit > 0
    ? Math.floor(configuredMessageLimit)
    : 2000;

const configuredAvailabilityPollMs = Number(
  import.meta.env.VITE_CHAT_AVAILABILITY_POLL_MS ?? "15000",
);
export const CHAT_AVAILABILITY_POLL_MS =
  Number.isFinite(configuredAvailabilityPollMs) && configuredAvailabilityPollMs >= 1_000
    ? Math.floor(configuredAvailabilityPollMs)
    : 15_000;
const CHAT_AVAILABILITY_FAILURE_TOLERANCE = 2;
const TURN_POLL_INTERVAL_MS = 3_000;

interface AvailabilityProbe {
  availability?: ChatAvailability;
  consecutiveFailures: number;
}

function availabilityMessage(
  availability: ChatAvailability | undefined,
  requestFailed: boolean,
): string {
  if (requestFailed) {
    return "No se pudo confirmar la disponibilidad del asistente. El historial continúa accesible.";
  }
  if (!availability) {
    return "Comprobando la disponibilidad del asistente…";
  }
  if (!availability.module_ready) {
    return "El asistente se está preparando. El resto de HemoVet continúa disponible.";
  }
  if (!availability.provider_ready) {
    return "El asistente está temporalmente no disponible. Puedes consultar conversaciones anteriores.";
  }
  if (availability.rag_required && !availability.rag_ready) {
    return "Las fuentes veterinarias requeridas no están disponibles temporalmente. Las conversaciones anteriores siguen accesibles.";
  }
  return "El asistente está disponible.";
}

// Every stage the backend actually emits over SSE gets a human label; the
// list below is the accumulating progress the user sees during the wait.
const stageLabels: Record<string, string> = {
  sending: "Enviando tu pregunta…",
  context_ready: "Contexto clínico verificado",
  retrieving: "Consultando fuentes veterinarias…",
  retrieval_completed: "Fuentes veterinarias consultadas",
  locating_nearby_care: "Buscando atención veterinaria cercana…",
  generating: "Generando y validando una respuesta segura…",
  validating: "Comprobando la seguridad clínica de la respuesta…",
  repairing: "Corrigiendo la respuesta antes de mostrarla…",
  stopping: "Deteniendo la generación…",
};

function initialScope(): ChatScope {
  const value = new URLSearchParams(window.location.search).get("scope");
  if (value === "selected_hemogram" || value === "uploaded_analysis") return "selected_hemogram";
  if (value === "hemogram_history" || value === "historical_analysis") return "hemogram_history";
  return "general";
}

// The canonical backend messages are exact but technical. Only the codes a
// person can actually act on are rewritten; the rest keep the backend text.
const errorOverridesByCode: Record<
  string,
  { message: string; recoveryAction?: ChatRecoveryAction }
> = {
  generation_repair_failed: {
    message:
      "La respuesta no pasó las comprobaciones de seguridad, así que no se mostró. Puedes volver a intentarlo.",
  },
  generation_queue_timeout: {
    message: "El asistente está ocupado con otra consulta. Vuelve a intentarlo en unos segundos.",
  },
  context_budget_exceeded: {
    message:
      "Hay demasiados datos clínicos para responder esto de una sola vez. Prueba con una pregunta más específica, por ejemplo sobre un solo valor o un solo estudio.",
    // A new conversation carries the same clinical context, so switching
    // conversations removes no evidence: only a narrower question helps.
    recoveryAction: "none",
  },
};

function friendlyError(caught: unknown): ErrorState {
  const envelope = chatErrorEnvelope(caught);
  if (envelope) {
    const override = errorOverridesByCode[envelope.code];
    return {
      message: override?.message ?? envelope.message,
      retryable: envelope.retryable,
      code: envelope.code,
      recoveryAction:
        override?.recoveryAction ??
        (envelope.recovery_action === "poll_turn" && !envelope.conversation_id
          ? "retry_same_turn"
          : envelope.recovery_action),
      retryAfterMs: envelope.retry_after_ms ?? undefined,
    };
  }
  if (caught instanceof ApiError) {
    if (caught.status === 404) {
      return {
        message: "El hemograma o la conversación ya no está disponible. Revisa el contexto activo.",
        retryable: false,
        recoveryAction: "choose_context",
      };
    }
    if (caught.status === 422) {
      return {
        message:
          "La solicitud del chat no es válida. Recarga la página y, si continúa, revisa la mascota o el hemograma seleccionado.",
        retryable: false,
        recoveryAction: "choose_context",
      };
    }
    if (caught.status === 429) {
      return {
        message: "Hay muchas solicitudes en curso. Espera un momento y vuelve a intentarlo.",
        retryable: true,
        recoveryAction: "retry_same_turn",
      };
    }
    if (caught.status === 503) {
      return {
        message:
          "El asistente está temporalmente no disponible. Tu pregunta se conserva para reintentarla.",
        retryable: true,
        recoveryAction: "retry_same_turn",
      };
    }
    if (caught.status === 401) {
      return {
        message: caught.message,
        retryable: false,
        recoveryAction: "none",
      };
    }
  }
  return {
    message:
      "No se pudo confirmar cómo terminó la respuesta. Tu pregunta se conserva para reintentarla.",
    retryable: true,
    recoveryAction: "retry_same_turn",
  };
}

const transientTurnStates = new Set<ChatTurnState>([
  "pending",
  "generating",
  "validating",
  "repairing",
]);
const retryableTurnStates = new Set<ChatTurnState>(["failed_retryable", "cancelled"]);

interface TurnStateSource {
  status: string;
  state?: ChatTurnState;
  processing_stage?: string | null;
  stage?: string | null;
  retryable: boolean;
  error_code?: string | null;
}

function canonicalTurnState(turn: TurnStateSource): ChatTurnState {
  if (turn.state) return turn.state;
  const processingStage = turn.processing_stage ?? turn.stage;
  if (
    processingStage &&
    [
      "pending",
      "generating",
      "validating",
      "repairing",
      "completed",
      "failed_retryable",
      "failed_terminal",
      "cancelled",
      "expired",
    ].includes(processingStage)
  ) {
    return processingStage as ChatTurnState;
  }
  if (turn.status === "completed" || turn.status === "refused") return "completed";
  if (turn.status === "interrupted") {
    return turn.error_code === "client_cancelled" ? "cancelled" : "expired";
  }
  if (turn.status === "failed" || turn.status === "incomplete") {
    return turn.retryable ? "failed_retryable" : "failed_terminal";
  }
  if (turn.status === "processing") return "generating";
  return "pending";
}

function isTransientTurn(state: ChatTurnState): boolean {
  return transientTurnStates.has(state);
}

function isRetryableTurn(state: ChatTurnState, retryable: boolean): boolean {
  if (state === "completed" || state === "failed_terminal" || state === "expired") return false;
  return retryableTurnStates.has(state) || retryable;
}

function streamContextIdentity(data: unknown): {
  conversationId?: string;
  contextRevision?: number;
  attempt?: number;
} {
  if (typeof data !== "object" || data === null) return {};
  const record = data as Record<string, unknown>;
  const nested =
    typeof record.context === "object" && record.context !== null
      ? (record.context as Record<string, unknown>)
      : undefined;
  const conversationId =
    typeof record.conversation_id === "string"
      ? record.conversation_id
      : typeof nested?.conversation_id === "string"
        ? nested.conversation_id
        : undefined;
  const revision =
    record.context_revision ?? record.revision ?? nested?.context_revision ?? nested?.revision;
  return {
    conversationId,
    contextRevision:
      typeof revision === "number" && Number.isInteger(revision) ? revision : undefined,
    attempt:
      typeof record.attempt === "number" && Number.isInteger(record.attempt)
        ? record.attempt
        : undefined,
  };
}

function canonicalConversationScope(mode: string): ChatScope | undefined {
  if (mode === "uploaded_analysis") return "selected_hemogram";
  if (mode === "historical_analysis") return "hemogram_history";
  return mode === "general" || mode === "selected_hemogram" || mode === "hemogram_history"
    ? mode
    : undefined;
}

function conversationMatchesContext(
  conversation: ChatConversation,
  scope: ChatScope,
  petId: string | undefined,
  analysisId: string | undefined,
): boolean {
  if (canonicalConversationScope(conversation.mode) !== scope) return false;
  if (scope === "general") return !conversation.pet_id && !conversation.analysis_id;
  if (scope === "selected_hemogram") return conversation.analysis_id === analysisId;
  return conversation.pet_id === petId;
}

function messagesFromConversationTurns(turns: ChatConversationTurn[]): Message[] {
  return [...turns]
    .sort((left, right) => left.turn_index - right.turn_index)
    .flatMap((turn): Message[] => {
      const restored: Message[] = [
        {
          id: turn.user_message.id,
          role: "user",
          text: turn.user_message.content,
          clientMessageId: turn.client_message_id,
          status: turn.user_message.status,
        },
      ];
      if (turn.response?.answer?.trim()) {
        restored.push({
          id: turn.response.message_id,
          role: "assistant",
          text: turn.response.answer,
          response: turn.response,
          clientMessageId: turn.client_message_id,
          status: turn.status,
        });
      }
      return restored;
    });
}

export function AssistantPage(): React.JSX.Element {
  const { user } = useAuth();
  const userId = user?.id;
  const { activePet, pets, setActivePetId } = useActivePet();
  const [scope, setScope] = useState<ChatScope>(initialScope);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<string | undefined>(
    () => new URLSearchParams(window.location.search).get("analysis_id") ?? undefined,
  );
  const [selectedAnalysisPetId, setSelectedAnalysisPetId] = useState<string | undefined>();
  const [selectionOrigin, setSelectionOrigin] = useState<"url" | "context">(() =>
    new URLSearchParams(window.location.search).has("analysis_id") ? "url" : "context",
  );
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string>();
  const [contextRevision, setContextRevision] = useState<number>();
  const [conversationContextKey, setConversationContextKey] = useState<string>();
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState(false);
  const [stage, setStage] = useState("sending");
  const [stageHistory, setStageHistory] = useState<string[]>([]);
  const [generationElapsedMs, setGenerationElapsedMs] = useState<number>();
  const [error, setError] = useState<ErrorState>();
  const [retryAttempt, setRetryAttempt] = useState<RetryAttempt>();
  const [retryDelaySeconds, setRetryDelaySeconds] = useState(0);
  const [contextNotice, setContextNotice] = useState<string>();
  const [conversationActionPending, setConversationActionPending] = useState(false);
  const [restoringConversation, setRestoringConversation] = useState(false);
  const [sessionEpoch, setSessionEpoch] = useState(0);
  const activeRequestRef = useRef<ActiveRequest | null>(null);
  const conversationActionRef = useRef<string | null>(null);
  const restoreComposerFocusRef = useRef(false);

  // The stage history accumulates so the wait shows completed steps instead
  // of a single mute line; each stage appears at most once per turn.
  const pushStage = useCallback((next: string) => {
    setStage(next);
    setStageHistory((current) => (current.includes(next) ? current : [...current, next]));
  }, []);
  const resetStageProgress = useCallback(() => {
    setStage("sending");
    setStageHistory([]);
  }, []);
  const recoveryButtonRef = useRef<HTMLButtonElement>(null);
  const restorationTokenRef = useRef(0);
  const initializedContextKeyRef = useRef<string | undefined>(undefined);
  const conversationIdRef = useRef<string | undefined>(undefined);
  const latestSessionEpochRef = useRef(sessionEpoch);
  const mountedRef = useRef(true);
  const pageActiveRef = useRef(document.visibilityState !== "hidden");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  conversationIdRef.current = conversationId;
  latestSessionEpochRef.current = sessionEpoch;

  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ["history", activePet?.id],
    queryFn: () => api.history({ petId: activePet?.id }),
    enabled: Boolean(user && activePet),
  });
  const lastAvailabilityRef = useRef<ChatAvailability | undefined>(undefined);
  const availabilityFailuresRef = useRef(0);
  const { data: availabilityProbe, refetch: refetchChatAvailability } = useQuery({
    queryKey: ["chat-availability", user?.id],
    queryFn: async (): Promise<AvailabilityProbe> => {
      try {
        const availability = await api.chatAvailability();
        lastAvailabilityRef.current = availability;
        availabilityFailuresRef.current = 0;
        return { availability, consecutiveFailures: 0 };
      } catch {
        // The provider probe has a 2 s budget while the GPU can stay busy far
        // longer, so an isolated failure is not evidence that generation
        // stopped working: keep the last confirmed verdict until a second
        // consecutive probe also fails.
        availabilityFailuresRef.current += 1;
        return {
          availability: lastAvailabilityRef.current,
          consecutiveFailures: availabilityFailuresRef.current,
        };
      }
    },
    enabled: Boolean(user),
    retry: false,
    refetchInterval: CHAT_AVAILABILITY_POLL_MS,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    staleTime: 0,
  });
  const chatAvailability = availabilityProbe?.availability;
  const failedAvailabilityProbes = availabilityProbe?.consecutiveFailures ?? 0;
  // Without a previous verdict there is nothing to protect, so a single failure
  // already fails closed.
  const chatAvailabilityError =
    failedAvailabilityProbes >= CHAT_AVAILABILITY_FAILURE_TOLERANCE ||
    (failedAvailabilityProbes > 0 && !chatAvailability);
  const chatReady = !chatAvailabilityError && chatAvailability?.chat_ready === true;
  const chatAvailabilityMessage = availabilityMessage(chatAvailability, chatAvailabilityError);
  const orderedHistory = useMemo(
    () =>
      [...history].sort(
        (left, right) => Date.parse(right.created_at) - Date.parse(left.created_at),
      ),
    [history],
  );
  const selectedFromHistory = orderedHistory.find((analysis) => analysis.id === selectedAnalysisId);
  const {
    data: exactAnalysis,
    isLoading: exactAnalysisLoading,
    isError: exactAnalysisError,
  } = useQuery({
    queryKey: ["analysis", selectedAnalysisId],
    queryFn: () => api.analysis(selectedAnalysisId as string),
    enabled: Boolean(
      user && scope === "selected_hemogram" && selectionOrigin === "url" && selectedAnalysisId,
    ),
    retry: false,
  });
  const selectedAnalysis =
    selectedFromHistory ??
    (exactAnalysis?.pet_id && exactAnalysis.pet_id === activePet?.id ? exactAnalysis : undefined);
  const effectiveAnalysisId = selectedAnalysis?.id;
  const activeContext = formatAssistantContext(
    scope,
    activePet,
    selectedAnalysis,
    orderedHistory.length,
  );
  const contextPetId = scope === "general" ? undefined : activePet?.id;
  const contextAnalysisId =
    scope === "selected_hemogram" ? (effectiveAnalysisId ?? selectedAnalysisId) : undefined;
  const contextKey = chatContextKey(scope, contextPetId, contextAnalysisId);
  const latestContextKeyRef = useRef(contextKey);
  latestContextKeyRef.current = contextKey;
  const contextReady =
    scope === "general" ||
    (scope === "hemogram_history"
      ? Boolean(activePet && orderedHistory.length > 0)
      : Boolean(activePet && selectedAnalysis));
  const awaitingExactPetSync =
    scope === "selected_hemogram" &&
    selectionOrigin === "url" &&
    Boolean(exactAnalysis?.pet_id && exactAnalysis.pet_id !== activePet?.id);
  const contextLoading =
    scope !== "general" &&
    (historyLoading ||
      (scope === "selected_hemogram" && selectionOrigin === "url" && exactAnalysisLoading) ||
      awaitingExactPetSync);
  const requestedAnalysisUnavailable =
    scope === "selected_hemogram" &&
    selectionOrigin === "url" &&
    Boolean(selectedAnalysisId) &&
    exactAnalysisError &&
    !selectedFromHistory;
  const contextSettled =
    conversationContextKey === contextKey && !restoringConversation && !conversationActionPending;
  const scrollTrigger =
    messages.length > 0 ? `${messages.length}:${messages.at(-1)?.text.length ?? 0}:${stage}` : "";

  useEffect(() => {
    if (!activePet) return;
    if (
      selectionOrigin === "context" &&
      selectedAnalysisPetId &&
      selectedAnalysisPetId !== activePet.id
    ) {
      setSelectedAnalysisId(undefined);
      setSelectedAnalysisPetId(undefined);
      return;
    }
    if (!selectedAnalysisId && orderedHistory.length > 0) {
      setSelectedAnalysisId(orderedHistory[0]?.id);
      setSelectedAnalysisPetId(activePet.id);
      setSelectionOrigin("context");
    }
  }, [activePet, orderedHistory, selectedAnalysisId, selectedAnalysisPetId, selectionOrigin]);

  useEffect(() => {
    if (scope !== "selected_hemogram" || selectionOrigin !== "url" || !selectedAnalysisId) return;
    const resolved = selectedFromHistory ?? exactAnalysis;
    const resolvedPetId = resolved?.pet_id ?? undefined;
    if (!resolvedPetId || !pets.some((pet) => pet.id === resolvedPetId)) return;
    setSelectedAnalysisPetId(resolvedPetId);
    if (activePet?.id !== resolvedPetId) {
      setActivePetId(resolvedPetId);
      return;
    }
    setSelectionOrigin("context");
  }, [
    activePet?.id,
    exactAnalysis,
    pets,
    selectedAnalysisId,
    selectedFromHistory,
    selectionOrigin,
    setActivePetId,
    scope,
  ]);

  useEffect(() => {
    const search = new URLSearchParams(window.location.search);
    if (scope === "general") search.delete("scope");
    else search.set("scope", scope);
    const analysisId = effectiveAnalysisId ?? selectedAnalysisId;
    if (scope === "selected_hemogram" && analysisId) {
      search.set("analysis_id", analysisId);
      const authorizedPetId = selectedAnalysis?.pet_id ?? selectedAnalysisPetId;
      if (authorizedPetId) search.set("pet_id", authorizedPetId);
      else search.delete("pet_id");
    } else {
      search.delete("analysis_id");
      search.delete("pet_id");
    }
    const query = search.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
    if (`${window.location.pathname}${window.location.search}${window.location.hash}` !== nextUrl) {
      window.history.replaceState(window.history.state, "", nextUrl);
    }
  }, [effectiveAnalysisId, scope, selectedAnalysis, selectedAnalysisId, selectedAnalysisPetId]);

  const cancelActiveRequest = useCallback(
    (
      reason: ActiveRequest["reason"],
      options: { detach?: boolean; notifyBackend?: boolean } = {},
    ) => {
      const activeRequest = activeRequestRef.current;
      if (!activeRequest) return;
      activeRequest.reason = reason;
      activeRequest.controller.abort();
      if (
        options.notifyBackend !== false &&
        activeRequest.conversationId &&
        activeRequest.attempt
      ) {
        void api
          .cancelChatTurn(
            activeRequest.conversationId,
            activeRequest.clientMessageId,
            activeRequest.attempt,
          )
          .catch(() => undefined);
      }
      if (options.detach !== false) activeRequestRef.current = null;
    },
    [],
  );

  const resetLocalConversation = useCallback(
    (notice: string, reason: ActiveRequest["reason"], options: { clearInput?: boolean } = {}) => {
      restorationTokenRef.current += 1;
      cancelActiveRequest(reason);
      conversationActionRef.current = null;
      if (userId) clearChatSessionManifest(userId, contextKey);
      conversationIdRef.current = undefined;
      setConversationId(undefined);
      setContextRevision(undefined);
      setConversationContextKey(undefined);
      setMessages([]);
      setPending(false);
      resetStageProgress();
      setError(undefined);
      setRetryAttempt(undefined);
      setContextNotice(notice);
      setConversationActionPending(false);
      setRestoringConversation(false);
      if (options.clearInput !== false) setInput("");
    },
    [cancelActiveRequest, contextKey, resetStageProgress, userId],
  );

  useEffect(() => {
    if (!userId || !pageActiveRef.current) return;
    if (initializedContextKeyRef.current === contextKey) return;

    const restorationToken = restorationTokenRef.current + 1;
    const requestedSessionEpoch = sessionEpoch;
    restorationTokenRef.current = restorationToken;
    cancelActiveRequest("context-change");
    conversationActionRef.current = null;

    conversationIdRef.current = undefined;
    setConversationActionPending(false);
    setConversationId(undefined);
    setContextRevision(undefined);
    setConversationContextKey(undefined);
    setMessages([]);
    setPending(false);
    resetStageProgress();
    setError(undefined);
    setRetryAttempt(undefined);
    setInput("");

    if (contextLoading) {
      setRestoringConversation(true);
      setContextNotice("Cargando y verificando el contexto clínico autorizado…");
      return;
    }

    if (!contextReady) {
      setRestoringConversation(false);
      setConversationContextKey(contextKey);
      setContextNotice(
        requestedAnalysisUnavailable
          ? "El hemograma solicitado no está disponible para esta cuenta. No se sustituyó por otro estudio."
          : `Contexto no disponible: ${activeContext.short}.`,
      );
      return;
    }

    const actionId = crypto.randomUUID();
    conversationActionRef.current = actionId;
    setConversationActionPending(true);
    setRestoringConversation(true);
    const persistedManifest = loadChatSessionManifest(userId, contextKey);
    const matchingManifest =
      persistedManifest?.scope === scope &&
      (scope === "general" || persistedManifest.petId === contextPetId) &&
      (scope !== "selected_hemogram" || persistedManifest.analysisId === contextAnalysisId)
        ? persistedManifest
        : undefined;
    if (persistedManifest && !matchingManifest) {
      clearChatSessionManifest(userId, contextKey);
    }
    setContextNotice(
      matchingManifest
        ? "Restaurando la conversación de esta sesión del navegador…"
        : "Buscando una conversación activa para este contexto…",
    );
    void (async () => {
      try {
        let reusable = matchingManifest
          ? {
              conversationId: matchingManifest.conversationId,
              contextRevision: matchingManifest.contextRevision,
            }
          : undefined;
        if (!reusable) {
          // The manifest only survives in this tab's sessionStorage, but the
          // backend indexes conversations by authenticated user: another tab or
          // a new browser session can still reuse the conversation that already
          // belongs to this context instead of starting an empty one. Reuse is
          // an optimization, so a failed lookup falls back to creating one.
          const conversations = await api.listChatConversations().catch(() => []);
          // Only reuse when the context identifies exactly one conversation.
          // The backend applies the same rule and says why: "If more than one
          // active, non-expired conversation matches, do not guess which one
          // the caller means". Taking the most recent match here would resume
          // a transcript the server deliberately refused to choose.
          const matches = conversations.filter((conversation) =>
            conversationMatchesContext(conversation, scope, contextPetId, contextAnalysisId),
          );
          const match = matches.length === 1 ? matches[0] : undefined;
          if (match) {
            reusable = { conversationId: match.id, contextRevision: match.context_revision };
          }
        }
        if (reusable) {
          try {
            const turns = await api.chatConversationTurns(reusable.conversationId);
            if (
              restorationTokenRef.current !== restorationToken ||
              latestSessionEpochRef.current !== requestedSessionEpoch ||
              conversationActionRef.current !== actionId ||
              latestContextKeyRef.current !== contextKey
            ) {
              return;
            }
            const lastTurn = [...turns].sort(
              (left, right) => right.turn_index - left.turn_index,
            )[0];
            conversationIdRef.current = reusable.conversationId;
            setConversationId(reusable.conversationId);
            setConversationContextKey(contextKey);
            setContextRevision(reusable.contextRevision);
            setMessages(messagesFromConversationTurns(turns));
            initializedContextKeyRef.current = contextKey;
            if (lastTurn) {
              const lastState = canonicalTurnState(lastTurn);
              // A transient state must be checked first: while the backend is
              // still processing the turn it reports `retryable: false`, so
              // asking `isRetryableTurn` first left a reload during generation
              // with no spinner and no way back to the pending answer.
              if (isTransientTurn(lastState)) {
                setRetryAttempt({
                  clientMessageId: lastTurn.client_message_id,
                  userMessageId: lastTurn.user_message.id,
                  text: lastTurn.user_message.content,
                });
                setError({
                  message:
                    "El asistente sigue preparando la respuesta de este turno. Se consultará su estado automáticamente.",
                  retryable: true,
                  code: lastTurn.error_code ?? lastState,
                  recoveryAction: "poll_turn",
                  tone: "status",
                });
              } else if (isRetryableTurn(lastState, lastTurn.retryable)) {
                setRetryAttempt({
                  clientMessageId: lastTurn.client_message_id,
                  userMessageId: lastTurn.user_message.id,
                  text: lastTurn.user_message.content,
                });
                setError({
                  message: "El último turno puede reintentarse sin perder la conversación.",
                  retryable: true,
                  code: lastTurn.error_code ?? lastState,
                  recoveryAction: "retry_same_turn",
                  tone: "status",
                });
              }
            }
            setContextNotice(`Conversación restaurada en ${activeContext.short.toLowerCase()}.`);
            return;
          } catch (caught) {
            if (!(caught instanceof ApiError) || caught.status !== 404) throw caught;
            clearChatSessionManifest(userId, contextKey);
          }
        }
        const created = await api.createChatConversation({
          context_scope: scope,
          analysis_id: scope === "selected_hemogram" ? contextAnalysisId : undefined,
          pet_id: scope !== "general" ? contextPetId : undefined,
        });
        if (
          restorationTokenRef.current !== restorationToken ||
          latestSessionEpochRef.current !== requestedSessionEpoch ||
          conversationActionRef.current !== actionId ||
          latestContextKeyRef.current !== contextKey
        ) {
          if (created && mountedRef.current && pageActiveRef.current) {
            void api.clearChatConversation(created.id).catch(() => undefined);
          }
          return;
        }
        if (!created) {
          throw new Error("El servidor no permite crear una conversación nueva.");
        }
        conversationIdRef.current = created.id;
        initializedContextKeyRef.current = contextKey;
        setConversationId(created.id);
        setConversationContextKey(contextKey);
        setContextRevision(created.context_revision);
        setContextNotice(`Chat nuevo listo en ${activeContext.short.toLowerCase()}.`);
      } catch {
        if (
          !mountedRef.current ||
          !pageActiveRef.current ||
          restorationTokenRef.current !== restorationToken ||
          latestSessionEpochRef.current !== requestedSessionEpoch ||
          conversationActionRef.current !== actionId
        ) {
          return;
        }
        initializedContextKeyRef.current = undefined;
        conversationIdRef.current = undefined;
        setConversationId(undefined);
        setContextRevision(undefined);
        setConversationContextKey(undefined);
        setMessages([]);
        setContextNotice("No se pudo iniciar una conversación nueva para este contexto.");
        setError({
          message: "No se pudo preparar una sesión nueva del asistente.",
          retryable: false,
          recoveryAction: "start_new_conversation",
        });
      } finally {
        if (
          mountedRef.current &&
          pageActiveRef.current &&
          restorationTokenRef.current === restorationToken &&
          latestSessionEpochRef.current === requestedSessionEpoch &&
          conversationActionRef.current === actionId
        ) {
          conversationActionRef.current = null;
          setConversationActionPending(false);
          setRestoringConversation(false);
        }
      }
    })();
  }, [
    activeContext.short,
    cancelActiveRequest,
    contextAnalysisId,
    contextKey,
    contextLoading,
    contextPetId,
    contextReady,
    requestedAnalysisUnavailable,
    resetStageProgress,
    scope,
    sessionEpoch,
    userId,
  ]);

  useEffect(() => {
    // Persist only opaque metadata. The authorized backend remains the source
    // of truth when this browser session restores the transcript.
    if (
      !userId ||
      !conversationId ||
      !contextRevision ||
      restoringConversation ||
      conversationContextKey !== contextKey
    ) {
      return;
    }
    const lastClientMessageId =
      retryAttempt?.clientMessageId ??
      [...messages].reverse().find((message) => message.clientMessageId)?.clientMessageId;
    saveChatSessionManifest({
      version: 2,
      userId,
      conversationId,
      contextRevision,
      scope,
      contextKey,
      petId: scope === "general" ? undefined : activePet?.id,
      analysisId: scope === "selected_hemogram" ? effectiveAnalysisId : undefined,
      lastClientMessageId,
      updatedAt: new Date().toISOString(),
    });
  }, [
    activePet?.id,
    contextKey,
    contextRevision,
    conversationId,
    conversationContextKey,
    effectiveAnalysisId,
    messages,
    restoringConversation,
    retryAttempt?.clientMessageId,
    scope,
    userId,
  ]);

  useEffect(() => {
    mountedRef.current = true;
    pageActiveRef.current = document.visibilityState !== "hidden";

    const pauseForPageExit = () => {
      if (!pageActiveRef.current) return;
      pageActiveRef.current = false;
      conversationActionRef.current = null;
      restorationTokenRef.current += 1;
      // Cancel in-flight work, but keep the opaque manifest. A page reload in
      // the same browser session must be able to restore the authorized turn.
      const activeRequest = activeRequestRef.current;
      cancelActiveRequest("unmount", { notifyBackend: false, detach: false });
      if (activeRequest) {
        setMessages((current) =>
          current
            .filter((message) => message.id !== activeRequest.assistantMessageId)
            .map((message) =>
              message.role === "user" && message.clientMessageId === activeRequest.clientMessageId
                ? { ...message, status: "interrupted" }
                : message,
            ),
        );
        setRetryAttempt(activeRequest.retryAttempt);
        setError({
          message: "La navegación interrumpió el turno. Puedes reintentar la misma pregunta.",
          retryable: true,
          code: "client_cancelled",
          recoveryAction: "retry_same_turn",
          tone: "status",
        });
        setPending(false);
        resetStageProgress();
      }
    };
    const resumePage = () => {
      if (pageActiveRef.current) return;
      pageActiveRef.current = true;
      if (
        activeRequestRef.current?.reason === "unmount" &&
        activeRequestRef.current.controller.signal.aborted
      ) {
        activeRequestRef.current = null;
      }
      // A restore/create operation may have been invalidated while the page
      // was hidden. Trigger the initialization effect only when no valid
      // conversation survived; an established conversation and its draft stay
      // untouched across BFCache/visibility transitions.
      if (!conversationIdRef.current) {
        initializedContextKeyRef.current = undefined;
        setConversationActionPending(false);
        setRestoringConversation(false);
        setSessionEpoch((current) => current + 1);
      }
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState !== "hidden") resumePage();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("pagehide", pauseForPageExit);
    window.addEventListener("pageshow", resumePage);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("pagehide", pauseForPageExit);
      window.removeEventListener("pageshow", resumePage);
      mountedRef.current = false;
      conversationActionRef.current = null;
      cancelActiveRequest("unmount", { notifyBackend: false });
      restorationTokenRef.current += 1;
    };
  }, [cancelActiveRequest, resetStageProgress]);

  useEffect(() => {
    if (pending || !restoreComposerFocusRef.current) return;
    textareaRef.current?.focus({ preventScroll: true });
    restoreComposerFocusRef.current = false;
  }, [pending]);

  useEffect(() => {
    if (pending || !error || error.recoveryAction === "none") return;
    recoveryButtonRef.current?.focus({ preventScroll: true });
  }, [error, pending]);

  useEffect(() => {
    if (!scrollTrigger) return;
    const marker = bottomRef.current;
    if (!marker || typeof marker.scrollIntoView !== "function") return;
    const reducedMotion =
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    marker.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "end" });
  }, [scrollTrigger]);

  const pollTurn = useCallback(async (): Promise<void> => {
    if (!conversationId || !retryAttempt || pending) return;
    setPending(true);
    try {
      const turn = await api.chatTurnStatus(conversationId, retryAttempt.clientMessageId);
      if (turn.response) {
        const response = turn.response;
        setMessages((current) => {
          const withoutResponse = current
            .filter((message) => message.id !== response.message_id)
            .map((message) =>
              message.role === "user" && message.clientMessageId === retryAttempt.clientMessageId
                ? { ...message, status: "completed" }
                : message,
            );
          return [
            ...withoutResponse,
            {
              id: response.message_id,
              role: "assistant" as const,
              text: response.answer,
              response,
              clientMessageId: retryAttempt.clientMessageId,
              status: "completed",
            },
          ];
        });
        setError(undefined);
        setRetryAttempt(undefined);
        return;
      }
      const turnState = canonicalTurnState(turn);
      if (isTransientTurn(turnState)) {
        setError({
          message: "El turno continúa en procesamiento. Espera un momento y consulta de nuevo.",
          retryable: true,
          code: turnState,
          recoveryAction: "poll_turn",
        });
      } else if (isRetryableTurn(turnState, turn.retryable)) {
        setError({
          message: "El turno ya puede reintentarse con el mismo identificador.",
          retryable: true,
          code: turn.error_code ?? turnState,
          recoveryAction: "retry_same_turn",
        });
      } else {
        setError({
          message:
            turnState === "expired"
              ? "El turno expiró y ya no puede recuperarse."
              : "El turno terminó sin una respuesta recuperable.",
          retryable: false,
          code: turn.error_code ?? turnState,
          recoveryAction: turnState === "expired" ? "start_new_conversation" : "none",
        });
        setRetryAttempt(undefined);
      }
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setPending(false);
      restoreComposerFocusRef.current = true;
    }
  }, [conversationId, pending, retryAttempt]);

  useEffect(() => {
    // A turn the backend is still processing resolves on its own, so it is
    // polled without waiting for the user to press "Consultar estado". Each
    // poll toggles `pending`, which reschedules this effect until the turn
    // reaches a state that no longer offers `poll_turn`.
    if (!conversationId || !retryAttempt || pending || error?.recoveryAction !== "poll_turn") {
      return;
    }
    const timer = window.setTimeout(() => void pollTurn(), TURN_POLL_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [conversationId, error?.recoveryAction, pending, pollTurn, retryAttempt]);

  useEffect(() => {
    // `retry_after_ms` is the backend's own pacing hint: honour it instead of
    // letting a retry land on the slot that is still busy.
    const waitMs = error?.retryAfterMs ?? 0;
    if (waitMs <= 0) {
      setRetryDelaySeconds(0);
      return;
    }
    const readyAt = Date.now() + waitMs;
    let timer = 0;
    const tick = () => {
      const remaining = Math.max(0, Math.ceil((readyAt - Date.now()) / 1000));
      setRetryDelaySeconds(remaining);
      if (remaining === 0) window.clearInterval(timer);
    };
    timer = window.setInterval(tick, 250);
    tick();
    return () => window.clearInterval(timer);
  }, [error]);

  if (!user) {
    return (
      <PrivateFeatureGate
        icon={Bot}
        description="El Chat LLM requiere iniciar sesión para usar contexto clínico autorizado. En modo invitado puedes subir un hemograma y revisar el resultado del modelo."
      />
    );
  }

  async function send(text = input, retry?: RetryAttempt): Promise<void> {
    const clean = text.trim();
    // `pending` is checked as well as `activeRequestRef`: the auto-poll for a
    // transient turn sets `pending` without ever setting the ref, so without
    // this a keystroke during a poll started a second stream, and the poll's
    // `finally` then cleared `pending` and rewrote state belonging to a turn
    // that was no longer the active one. The composer stays editable; only
    // the send is refused.
    if (
      !clean ||
      pending ||
      activeRequestRef.current ||
      restoringConversation ||
      conversationActionPending
    ) {
      return;
    }
    if (!chatReady) {
      setContextNotice(chatAvailabilityMessage);
      return;
    }
    if (!contextReady) {
      setError({
        message:
          scope === "hemogram_history"
            ? "Selecciona una mascota con hemogramas para consultar su historial."
            : "Selecciona un hemograma antes de usar este contexto.",
        retryable: false,
        recoveryAction: "choose_context",
      });
      return;
    }
    if (!contextSettled) {
      setContextNotice("Preparando una conversación compatible con el contexto activo…");
      return;
    }

    const attempt: RetryAttempt = retry ?? {
      clientMessageId: crypto.randomUUID(),
      userMessageId: crypto.randomUUID(),
      text: clean,
    };
    const assistantMessageId = crypto.randomUUID();
    const requestId = crypto.randomUUID();
    const controller = new AbortController();
    let requestConversationId = conversationId;
    activeRequestRef.current = {
      id: requestId,
      assistantMessageId,
      clientMessageId: attempt.clientMessageId,
      controller,
      conversationId,
      retryAttempt: attempt,
    };

    if (!retry) {
      setMessages((current) => [
        ...current,
        {
          id: attempt.userMessageId,
          role: "user",
          text: clean,
          clientMessageId: attempt.clientMessageId,
          status: "pending",
        },
      ]);
    }
    setInput("");
    setPending(true);
    setStage("sending");
    setStageHistory(["sending"]);
    setGenerationElapsedMs(undefined);
    setError(undefined);
    setRetryAttempt(undefined);
    setContextNotice(undefined);

    const requestIsCurrent = () => activeRequestRef.current?.id === requestId;
    const revealAssistantAnswer = (answer: string) => {
      if (!requestIsCurrent()) return;
      setMessages((current) => {
        let found = false;
        const next = current.map((message) => {
          if (message.id !== assistantMessageId) return message;
          found = true;
          return { ...message, text: answer };
        });
        return found
          ? next
          : [
              ...current,
              {
                id: assistantMessageId,
                role: "assistant" as const,
                text: answer,
                clientMessageId: attempt.clientMessageId,
                status: "processing",
              },
            ];
      });
    };
    const replaceAssistantResponse = (response: ChatResponse) => {
      if (!requestIsCurrent()) return;
      setMessages((current) => {
        const withoutDraft = current
          .filter((message) => message.id !== assistantMessageId)
          .map((message) =>
            message.role === "user" && message.clientMessageId === attempt.clientMessageId
              ? { ...message, status: "completed" }
              : message,
          );
        return [
          ...withoutDraft,
          {
            id: response.message_id,
            role: "assistant" as const,
            text: response.answer,
            response,
            clientMessageId: attempt.clientMessageId,
            status: "completed",
          },
        ];
      });
    };

    try {
      const response = await api.streamChat(
        {
          client_message_id: attempt.clientMessageId,
          conversation_id: conversationId,
          message: clean,
          context_scope: scope,
          analysis_id: scope === "selected_hemogram" ? effectiveAnalysisId : undefined,
          pet_id: scope !== "general" ? activePet?.id : undefined,
          expected_context_revision: contextRevision,
          options: {},
        },
        {
          signal: controller.signal,
          onEvent: (event) => {
            if (!requestIsCurrent()) return;
            if (event.event === "start") {
              const identity = streamContextIdentity(event.data);
              if (identity.conversationId) {
                requestConversationId = identity.conversationId;
                setConversationId(identity.conversationId);
                setConversationContextKey(contextKey);
                if (activeRequestRef.current?.id === requestId) {
                  activeRequestRef.current.conversationId = identity.conversationId;
                }
              }
              if (identity.contextRevision !== undefined) {
                setContextRevision(identity.contextRevision);
              }
              if (identity.attempt !== undefined && activeRequestRef.current?.id === requestId) {
                activeRequestRef.current.attempt = identity.attempt;
              }
            }
            if (event.event === "context_ready") {
              pushStage("context_ready");
            }
            if (event.event === "retrieval_completed") {
              pushStage("retrieval_completed");
            }
            if (event.event === "generation_started") {
              pushStage("generating");
            }
            if (
              event.event === "heartbeat" &&
              typeof event.data === "object" &&
              event.data !== null &&
              "elapsed_ms" in event.data &&
              typeof event.data.elapsed_ms === "number"
            ) {
              // A turn can take minutes; the heartbeat is the only progress
              // signal the backend emits while the GPU works.
              setGenerationElapsedMs(event.data.elapsed_ms);
            }
            if (
              event.event === "status" &&
              typeof event.data === "object" &&
              event.data !== null &&
              "stage" in event.data &&
              typeof event.data.stage === "string"
            ) {
              pushStage(event.data.stage);
            }
            if (
              event.event === "final" &&
              typeof event.data === "object" &&
              event.data !== null &&
              "answer" in event.data &&
              typeof event.data.answer === "string"
            ) {
              revealAssistantAnswer(event.data.answer);
            }
          },
        },
      );
      if (!requestIsCurrent()) return;
      setConversationId(response.conversation_id);
      setConversationContextKey(contextKey);
      requestConversationId = response.conversation_id;
      const responseContext = streamContextIdentity(response.context);
      if (responseContext.contextRevision !== undefined) {
        setContextRevision(responseContext.contextRevision);
      }
      replaceAssistantResponse(response);
      setRetryAttempt(undefined);
    } catch (caught) {
      if (!requestIsCurrent()) return;
      const activeReason = activeRequestRef.current?.reason;
      setMessages((current) =>
        current
          .filter((message) => message.id !== assistantMessageId)
          .map((message) =>
            message.role === "user" && message.clientMessageId === attempt.clientMessageId
              ? {
                  ...message,
                  status:
                    activeReason === "stop" || activeReason === "unmount"
                      ? "interrupted"
                      : "failed",
                }
              : message,
          ),
      );
      if (caught instanceof DOMException && caught.name === "AbortError") {
        if (activeReason === "stop") {
          setError({
            message: "La generación se detuvo. Puedes reintentar la misma pregunta.",
            retryable: true,
            code: "client_cancelled",
            recoveryAction: "retry_same_turn",
            tone: "status",
          });
          setRetryAttempt(attempt);
        }
        return;
      }
      const envelope = chatErrorEnvelope(caught);
      const originalError = friendlyError(caught);
      if (
        envelope?.code.startsWith("LLM_PROVIDER_") ||
        (caught instanceof ApiError && caught.status === 503)
      ) {
        void refetchChatAvailability();
      }
      requestConversationId = envelope?.conversation_id ?? requestConversationId;
      if (requestConversationId && envelope?.recovery_action !== "start_new_conversation") {
        try {
          const turn = await api.chatTurnStatus(requestConversationId, attempt.clientMessageId);
          if (!requestIsCurrent()) return;
          if (turn.response) {
            setConversationId(turn.conversation_id);
            replaceAssistantResponse(turn.response);
            setError(undefined);
            setRetryAttempt(undefined);
            return;
          }
          const turnState = canonicalTurnState(turn);
          if (isTransientTurn(turnState)) {
            setError({
              message:
                "El backend todavía está procesando este turno. Consulta su estado antes de reenviarlo.",
              retryable: true,
              code: "turn_in_progress",
              recoveryAction: "poll_turn",
            });
            setRetryAttempt(attempt);
            return;
          }
          if (isRetryableTurn(turnState, turn.retryable)) {
            setError({
              ...originalError,
              retryable: true,
              code: turn.error_code ?? originalError.code ?? turnState,
              recoveryAction: "retry_same_turn",
            });
            setRetryAttempt(attempt);
            return;
          }
          setError({
            message:
              turnState === "expired"
                ? "El turno expiró y ya no puede recuperarse."
                : "El turno terminó sin una respuesta recuperable.",
            retryable: false,
            code: turn.error_code ?? turnState,
            recoveryAction: turnState === "expired" ? "start_new_conversation" : "none",
          });
          setRetryAttempt(undefined);
          return;
        } catch {
          // The original typed error remains the best available recovery signal.
        }
      }
      setError(originalError);
      setRetryAttempt(originalError.retryable ? attempt : undefined);
    } finally {
      if (requestIsCurrent()) {
        activeRequestRef.current = null;
        restoreComposerFocusRef.current = true;
        setPending(false);
        resetStageProgress();
        setGenerationElapsedMs(undefined);
      }
    }
  }

  function stopGeneration(): void {
    const activeRequest = activeRequestRef.current;
    if (!activeRequest) return;
    pushStage("stopping");
    cancelActiveRequest("stop", { detach: false });
  }

  async function replaceConversation(
    reason: "new-chat" | "clear",
    preparingNotice: string,
    readyNotice: string,
  ): Promise<void> {
    const remoteConversationId = conversationIdRef.current;
    resetLocalConversation(preparingNotice, reason);
    if (!contextReady) return;

    const actionId = crypto.randomUUID();
    const requestedContextKey = contextKey;
    conversationActionRef.current = actionId;
    setConversationActionPending(true);
    setRestoringConversation(true);
    try {
      if (remoteConversationId) {
        await api.clearChatConversation(remoteConversationId).catch(() => false);
      }
      const created = await api.createChatConversation({
        context_scope: scope,
        analysis_id: scope === "selected_hemogram" ? effectiveAnalysisId : undefined,
        pet_id: scope !== "general" ? activePet?.id : undefined,
      });
      if (
        conversationActionRef.current !== actionId ||
        latestContextKeyRef.current !== requestedContextKey
      ) {
        if (created) void api.clearChatConversation(created.id).catch(() => undefined);
        return;
      }
      if (!created) {
        throw new Error("El servidor no permite crear una conversación nueva.");
      }
      initializedContextKeyRef.current = contextKey;
      conversationIdRef.current = created.id;
      setConversationId(created.id);
      setContextRevision(created.context_revision);
      setConversationContextKey(contextKey);
      setContextNotice(readyNotice);
    } catch {
      if (conversationActionRef.current !== actionId) return;
      initializedContextKeyRef.current = undefined;
      conversationIdRef.current = undefined;
      setError({
        message: "El chat se reinició localmente, pero no se pudo preparar la sesión remota.",
        retryable: false,
        recoveryAction: "start_new_conversation",
      });
    } finally {
      if (conversationActionRef.current === actionId) {
        conversationActionRef.current = null;
        setConversationActionPending(false);
        setRestoringConversation(false);
      }
    }
  }

  async function startNewConversation(): Promise<void> {
    await replaceConversation(
      "new-chat",
      `Iniciando un chat nuevo en ${activeContext.short.toLowerCase()}…`,
      `Nuevo chat listo en ${activeContext.short.toLowerCase()}.`,
    );
  }

  async function clearConversation(): Promise<void> {
    await replaceConversation(
      "clear",
      "Eliminando la conversación anterior…",
      "La conversación anterior se eliminó. El chat está vacío y listo para comenzar.",
    );
  }

  const scopeLabel =
    scope === "general"
      ? "General"
      : scope === "hemogram_history"
        ? "Historial"
        : "Hemograma seleccionado";
  const composerPlaceholder = !chatReady
    ? "El asistente está temporalmente no disponible"
    : scope === "general"
      ? "Escribe una pregunta sobre el hemograma..."
      : scope === "hemogram_history"
        ? "Pregunta por cambios entre los hemogramas..."
        : "Escribe una pregunta sobre el hemograma...";

  return (
    <div className="assistant-page page-flow">
      <PageHeader
        eyebrow="Asistente con fuentes"
        title="Explicaciones sobre el hemograma"
        description="Selecciona exactamente qué información puede usar el asistente para responder."
        actions={
          <>
            <button
              className="button button--secondary"
              type="button"
              onClick={() => void startNewConversation()}
              disabled={conversationActionPending}
            >
              <Plus size={17} aria-hidden="true" /> Nuevo chat
            </button>
            <button
              className="button button--ghost"
              type="button"
              onClick={() => void clearConversation()}
              disabled={
                conversationActionPending || (!pending && messages.length === 0 && !conversationId)
              }
            >
              <Eraser size={17} aria-hidden="true" /> Limpiar
            </button>
          </>
        }
      />

      <div className="assistant-layout">
        <aside className="assistant-context">
          <fieldset className="context-options" aria-label="Contexto del asistente">
            <legend className="eyebrow">Contexto de respuesta</legend>
            {[
              {
                value: "general" as const,
                title: "Chat general",
                detail: "Conceptos sin usar datos clínicos.",
                icon: MessageCircle,
              },
              {
                value: "selected_hemogram" as const,
                title: "Hemograma seleccionado",
                detail: selectedAnalysis
                  ? `${activePet?.name ?? "Mascota"} · ${new Date(selectedAnalysis.created_at).toLocaleDateString("es-DO")}`
                  : historyLoading
                    ? "Cargando estudios…"
                    : "Sin resultado disponible",
                icon: BookOpen,
              },
              {
                value: "hemogram_history" as const,
                title: "Historial de hemogramas",
                detail: `${orderedHistory.length} ${orderedHistory.length === 1 ? "estudio" : "estudios"} de ${activePet?.name ?? "la mascota"}.`,
                icon: History,
              },
            ].map((option) => {
              const Icon = option.icon;
              const unavailable =
                option.value !== "general" &&
                orderedHistory.length === 0 &&
                !(option.value === "selected_hemogram" && selectedAnalysis);
              return (
                <label
                  className="context-option"
                  data-active={scope === option.value}
                  data-disabled={unavailable}
                  key={option.value}
                >
                  <input
                    type="radio"
                    name="assistant-context"
                    value={option.value}
                    checked={scope === option.value}
                    disabled={unavailable}
                    onChange={() => setScope(option.value)}
                  />
                  <span className="radio-indicator" aria-hidden="true" />
                  <Icon className="context-option__icon" size={18} aria-hidden="true" />
                  <span>
                    <strong>{option.title}</strong>
                    <small>{option.detail}</small>
                  </span>
                </label>
              );
            })}
          </fieldset>

          {scope === "selected_hemogram" && orderedHistory.length > 0 && (
            <label className="field-label" htmlFor="assistant-analysis">
              Hemograma activo
              <select
                id="assistant-analysis"
                value={effectiveAnalysisId ?? ""}
                onChange={(event) => {
                  setSelectedAnalysisId(event.target.value);
                  setSelectedAnalysisPetId(activePet?.id);
                  setSelectionOrigin("context");
                }}
              >
                {!effectiveAnalysisId && selectedAnalysisId && (
                  <option value="" disabled>
                    El hemograma solicitado no está disponible
                  </option>
                )}
                {orderedHistory.map((analysis) => (
                  <option value={analysis.id} key={analysis.id}>
                    {new Date(analysis.created_at).toLocaleDateString("es-DO")} · {analysis.summary}
                  </option>
                ))}
              </select>
            </label>
          )}

          <section className="assistant-active-context" aria-label="Contexto clínico activo">
            <strong>{activeContext.short}</strong>
            <span>{activeContext.detail}</span>
          </section>

          <section className="assistant-limits">
            <ShieldAlert size={19} aria-hidden="true" />
            <div>
              <strong>Límites activos</strong>
              <ul>
                <li>No emite diagnósticos.</li>
                <li>No indica medicamentos, tratamientos ni dosis.</li>
                <li>Una urgencia requiere atención veterinaria.</li>
              </ul>
            </div>
          </section>
        </aside>

        <section className="chat-panel" data-tour="asistente-chat">
          <header className="chat-panel__header">
            <div>
              <span className="assistant-avatar">
                <Bot size={20} aria-hidden="true" />
              </span>
              <div>
                <strong>Asistente HemoVet</strong>
                <small>Orientación educativa con contexto autorizado</small>
              </div>
            </div>
            <div className="chat-panel__badges">
              <StatusBadge tone={chatReady ? "success" : "warn"}>
                {chatReady ? "Asistente disponible" : "Chat en pausa"}
              </StatusBadge>
              <StatusBadge tone="neutral">Contexto: {scopeLabel}</StatusBadge>
            </div>
          </header>

          {!chatReady && (
            <output className="chat-availability" aria-live="polite">
              <AlertTriangle size={19} aria-hidden="true" />
              <div>
                <strong>Generación temporalmente en pausa</strong>
                <p>{chatAvailabilityMessage}</p>
              </div>
            </output>
          )}

          {error && (
            <div
              className="chat-error"
              data-tone={error.tone ?? "error"}
              role={error.tone === "status" ? "status" : "alert"}
            >
              <AlertTriangle size={19} aria-hidden="true" />
              <div>
                <strong>
                  {error.tone === "status" ? "Generación detenida" : "No se completó la respuesta"}
                </strong>
                <p>{error.message}</p>
                <div className="chat-error__actions">
                  {error.recoveryAction === "retry_same_turn" && retryAttempt && (
                    <button
                      ref={recoveryButtonRef}
                      className="button button--secondary"
                      type="button"
                      onClick={() => void send(retryAttempt.text, retryAttempt)}
                      disabled={pending || retryDelaySeconds > 0}
                    >
                      <RefreshCw size={16} aria-hidden="true" /> Reintentar
                      {retryDelaySeconds > 0 && ` en ${retryDelaySeconds} s`}
                    </button>
                  )}
                  {error.recoveryAction === "poll_turn" && retryAttempt && (
                    <button
                      ref={recoveryButtonRef}
                      className="button button--secondary"
                      type="button"
                      onClick={() => void pollTurn()}
                      disabled={pending}
                    >
                      <RefreshCw size={16} aria-hidden="true" /> Consultar estado
                    </button>
                  )}
                  {(error.recoveryAction === "start_new_conversation" ||
                    error.recoveryAction === "choose_context") && (
                    <button
                      ref={recoveryButtonRef}
                      className="button button--secondary"
                      type="button"
                      onClick={() => void startNewConversation()}
                      disabled={pending || conversationActionPending}
                    >
                      <Plus size={16} aria-hidden="true" /> Iniciar chat compatible
                    </button>
                  )}
                  <button
                    className="button button--ghost"
                    type="button"
                    onClick={() => setError(undefined)}
                  >
                    <X size={16} aria-hidden="true" /> Cerrar
                  </button>
                </div>
              </div>
            </div>
          )}

          <div
            className="chat-messages"
            role="log"
            aria-label="Conversación con el asistente HemoVet"
            aria-live="polite"
            aria-relevant="additions text"
            aria-busy={pending || restoringConversation}
          >
            {messages.length === 0 && (
              <div className="chat-empty">
                <Bot size={28} aria-hidden="true" />
                <h2>¿Qué necesitas entender?</h2>
                <p>Las respuestas mostrarán referencias legibles cuando se use el corpus.</p>
                <fieldset className="suggestion-list">
                  <legend className="sr-only">Preguntas sugeridas</legend>
                  {suggestionsByScope[scope].map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => void send(suggestion)}
                      disabled={
                        pending ||
                        restoringConversation ||
                        !contextReady ||
                        !contextSettled ||
                        !chatReady
                      }
                    >
                      {suggestion}
                    </button>
                  ))}
                </fieldset>
              </div>
            )}
            {messages.map((message) => {
              const sources = message.response ? visibleChatSources(message.response.sources) : [];
              return (
                <article className="chat-message" data-role={message.role} key={message.id}>
                  <span className="chat-message__avatar">
                    {message.role === "assistant" ? (
                      <Bot size={17} aria-hidden="true" />
                    ) : (
                      <User size={17} aria-hidden="true" />
                    )}
                  </span>
                  <div>
                    <strong>{message.role === "assistant" ? "HemoVet" : "Tú"}</strong>
                    <p>{message.text}</p>
                    {message.response && (
                      <>
                        {message.response.case_facts.length > 0 && (
                          <div className="case-facts">
                            <span>Datos utilizados</span>
                            <dl>
                              {message.response.case_facts.map((fact, index) => {
                                const date = fact.study_date
                                  ? new Date(fact.study_date)
                                  : undefined;
                                const dateLabel =
                                  date && !Number.isNaN(date.getTime())
                                    ? date.toLocaleDateString("es-DO", {
                                        day: "numeric",
                                        month: "short",
                                        year: "numeric",
                                      })
                                    : undefined;
                                const value =
                                  fact.unit &&
                                  !fact.value.toLowerCase().includes(fact.unit.toLowerCase())
                                    ? `${fact.value} ${fact.unit}`
                                    : fact.value;
                                const status =
                                  fact.status === "high"
                                    ? "Alto"
                                    : fact.status === "low"
                                      ? "Bajo"
                                      : fact.status === "normal"
                                        ? "En rango"
                                        : undefined;
                                const range =
                                  fact.reference_min != null && fact.reference_max != null
                                    ? `Rango: ${fact.reference_min}–${fact.reference_max}${fact.unit ? ` ${fact.unit}` : ""}`
                                    : undefined;
                                const metadata = [fact.study_key, dateLabel, status, range].filter(
                                  (item): item is string => Boolean(item),
                                );
                                return (
                                  <div
                                    key={`${fact.analysis_id ?? fact.study_key ?? dateLabel ?? "study"}-${fact.parameter}-${fact.value}-${index}`}
                                  >
                                    <dt>{fact.parameter}</dt>
                                    <dd>
                                      <span>{value}</span>
                                      {metadata.length > 0 && (
                                        <small className="case-fact__meta">
                                          {metadata.join(" · ")}
                                        </small>
                                      )}
                                    </dd>
                                  </div>
                                );
                              })}
                            </dl>
                          </div>
                        )}
                        {sources.length > 0 && (
                          <details className="source-details">
                            <summary>
                              <BookOpen size={15} aria-hidden="true" /> Ver fuentes (
                              {sources.length})
                            </summary>
                            <ol>
                              {sources.map((source) => (
                                <li key={source.key}>
                                  <cite>{source.title}</cite>
                                  {source.details.map((detail) => (
                                    <span key={detail}>{detail}</span>
                                  ))}
                                </li>
                              ))}
                            </ol>
                          </details>
                        )}
                        {message.response.warnings.map((warning) => (
                          <small className="message-warning" key={warning}>
                            {warning}
                          </small>
                        ))}
                      </>
                    )}
                  </div>
                </article>
              );
            })}
            <div ref={bottomRef} aria-hidden="true" />
          </div>

          <output className="chat-live-status" aria-live="polite" aria-atomic="false">
            {restoringConversation ? (
              (contextNotice ?? "Preparando la conversación…")
            ) : pending ? (
              <ol className="chat-stage-list">
                {(stageHistory.length > 0 ? stageHistory : [stage]).map((item, index, list) => {
                  const isCurrent = index === list.length - 1;
                  return (
                    <li
                      key={item}
                      className={
                        isCurrent ? "chat-stage chat-stage-current" : "chat-stage chat-stage-done"
                      }
                    >
                      {isCurrent ? (
                        <LoaderCircle
                          className="chat-status-spinner"
                          size={15}
                          aria-hidden="true"
                        />
                      ) : (
                        <Check className="chat-stage-check" size={15} aria-hidden="true" />
                      )}
                      {stageLabels[item] ?? "Procesando la respuesta…"}
                      {isCurrent &&
                        generationElapsedMs !== undefined &&
                        ` · ${Math.round(generationElapsedMs / 1000)} s`}
                    </li>
                  );
                })}
              </ol>
            ) : (
              (contextNotice ?? "")
            )}
          </output>

          <form
            className="chat-composer"
            data-tour="asistente-composer"
            onSubmit={(event) => {
              event.preventDefault();
              void send();
            }}
          >
            <label>
              <span className="sr-only">Pregunta para el asistente</span>
              <textarea
                ref={textareaRef}
                rows={2}
                maxLength={CHAT_MESSAGE_MAX_CHARS}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault();
                    void send();
                  }
                }}
                placeholder={composerPlaceholder}
                aria-describedby="assistant-composer-help"
                // `send()` already refuses to start a second turn, so keeping the
                // draft editable while one is generating costs nothing.
                disabled={restoringConversation || !contextReady || !contextSettled || !chatReady}
              />
            </label>
            {pending ? (
              <button
                className="button button--danger"
                type="button"
                onClick={stopGeneration}
                aria-label="Detener generación"
              >
                <Square size={17} aria-hidden="true" />
              </button>
            ) : (
              <button
                className="button button--primary"
                type="submit"
                disabled={
                  !input.trim() ||
                  restoringConversation ||
                  !contextReady ||
                  !contextSettled ||
                  !chatReady
                }
                aria-label="Enviar pregunta"
              >
                <Send size={18} aria-hidden="true" />
              </button>
            )}
            <small id="assistant-composer-help" className="chat-composer__help">
              Enter para enviar · Mayús + Enter para una nueva línea
            </small>
          </form>
        </section>
      </div>
    </div>
  );
}
