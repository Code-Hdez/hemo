import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StrictMode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../app/api";
import type { AnalysisResult, ChatAvailability, ChatResponse } from "../domain/types";
import { AssistantPage, CHAT_AVAILABILITY_POLL_MS } from "./AssistantPage";

vi.mock("../app/AuthContext", () => ({
  useAuth: () => ({ user: { id: "owner-1", full_name: "Ana" } }),
}));

vi.mock("../app/PetContext", () => {
  const activePet = {
    id: "pet-1",
    owner_id: "owner-1",
    name: "Luna",
    residence_consent: false,
    created_at: "2026-01-01T00:00:00Z",
  };
  return {
    useActivePet: () => ({
      pets: [activePet],
      activePet,
      activePetId: activePet.id,
      setActivePetId: vi.fn(),
      loading: false,
      error: null,
      refetch: vi.fn(),
    }),
  };
});

vi.mock("../app/api", async () => {
  const actual = await vi.importActual<typeof import("../app/api")>("../app/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      history: vi.fn(),
      chatAvailability: vi.fn(),
      streamChat: vi.fn(),
      listChatConversations: vi.fn(),
      createChatConversation: vi.fn(),
      clearChatConversation: vi.fn(),
      chatTurnStatus: vi.fn(),
      chatConversationTurns: vi.fn(),
      cancelChatTurn: vi.fn(),
    },
  };
});

const analyses: AnalysisResult[] = [
  {
    id: "analysis-july",
    status: "success",
    imputed_fields: [],
    extraction_warnings: [],
    filename: "luna-julio.pdf",
    file_size: 1200,
    created_at: "2026-07-15T12:00:00Z",
    confidence: 0.95,
    quality_score: 0.94,
    species: "Canina",
    summary: "Control de julio",
    diagnoses: [],
    findings: [],
    qc_flags: [],
    lab_values: [],
    pet_id: "pet-1",
    persisted: true,
  },
  {
    id: "analysis-march",
    status: "success",
    imputed_fields: [],
    extraction_warnings: [],
    filename: "luna-marzo.pdf",
    file_size: 1100,
    created_at: "2026-03-14T12:00:00Z",
    confidence: 0.92,
    quality_score: 0.91,
    species: "Canina",
    summary: "Control de marzo",
    diagnoses: [],
    findings: [],
    qc_flags: [],
    lab_values: [],
    pet_id: "pet-1",
    persisted: true,
  },
];

function chatResponse(sources: ChatResponse["sources"] = []): ChatResponse {
  return {
    conversation_id: "conversation-1",
    message_id: "assistant-1",
    answer: "Los leucocitos son células de defensa.",
    scope: "general",
    sources,
    case_facts: [],
    warnings: [],
    safety_action: "allow",
    model: "qwen",
    usage: { prompt_tokens: 20, completion_tokens: 8 },
    duration_ms: 20,
    finish_reason: "stop",
    llm_invoked: true,
    response_origin: "llm",
    attempt: 1,
    generation_attempts: 1,
    stream_mode: "buffered_validated",
    validation_status: "passed",
  };
}

function chatAvailability(providerReady = true, ragReady = true): ChatAvailability {
  const chatReady = providerReady && ragReady;
  return {
    contract_version: "hemovet.availability/v1",
    probe: "chat_availability",
    status: chatReady ? "ok" : "degraded",
    chat_ready: chatReady,
    degraded: providerReady && !ragReady,
    module_ready: true,
    provider_ready: providerReady,
    llm_ready: providerReady,
    rag_required: true,
    rag_ready: ragReady,
    chroma_ready: ragReady,
    collection_ready: ragReady,
    codes: providerReady ? (ragReady ? [] : ["rag_not_ready"]) : ["LLM_PROVIDER_UNAVAILABLE"],
    provider: {
      contract_version: "hemovet.availability/v1",
      probe: "provider_availability",
      status: providerReady ? "ready" : "unavailable",
      provider: "test-provider",
      model: "qwen3:4b",
      ready: providerReady,
      code: providerReady ? null : "LLM_PROVIDER_UNAVAILABLE",
      retryable: !providerReady,
      identity_verified: providerReady,
    },
    rag: {
      contract_version: "hemovet.availability/v1",
      probe: "rag_availability",
      status: ragReady ? "ready" : "unavailable",
      required: true,
      ready: ragReady,
      chroma_ready: ragReady,
      collection_ready: ragReady,
      index_ready: ragReady,
      codes: ragReady ? [] : ["rag_not_ready"],
    },
    rag_enabled: true,
    rag_issue: ragReady ? null : "rag_not_ready",
    chunk_count: ragReady ? 100 : 0,
    embedding_model: "test-embedding-model",
    index_fingerprint: "test-fingerprint",
    runtime: {
      provider: "test-provider",
      model: "qwen3:4b",
      installed: providerReady,
      loaded: providerReady,
      gpu_active: providerReady,
      gpu_memory_bytes: providerReady ? 1000 : null,
      inference_device: providerReady ? "cuda" : "unknown",
      residency_observed: providerReady,
      identity_verified: providerReady,
      identity_error_code: providerReady ? null : "LLM_PROVIDER_UNAVAILABLE",
    },
    runtime_identity_error: providerReady ? null : "LLM_PROVIDER_UNAVAILABLE",
    gpu_active: providerReady,
    gpu_memory_bytes: providerReady ? 1000 : null,
    inference_device: providerReady ? "cuda" : "unknown",
    provider_contract: null,
  };
}

function renderAssistantPage(options: { strict?: boolean } = {}): ReturnType<typeof render> {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const page = (
    <QueryClientProvider client={queryClient}>
      <AssistantPage />
    </QueryClientProvider>
  );
  return render(options.strict ? <StrictMode>{page}</StrictMode> : page);
}

async function waitForChatReady(): Promise<void> {
  await waitFor(() =>
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeEnabled(),
  );
}

describe("AssistantPage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    window.history.replaceState({}, "", "/asistente");
    vi.mocked(api.history).mockResolvedValue(analyses);
    vi.mocked(api.chatAvailability).mockReset();
    vi.mocked(api.chatAvailability).mockResolvedValue(chatAvailability());
    vi.mocked(api.streamChat).mockReset();
    vi.mocked(api.listChatConversations).mockReset();
    vi.mocked(api.listChatConversations).mockResolvedValue([]);
    vi.mocked(api.createChatConversation).mockReset();
    vi.mocked(api.clearChatConversation).mockReset();
    vi.mocked(api.chatTurnStatus).mockReset();
    vi.mocked(api.chatConversationTurns).mockReset();
    vi.mocked(api.cancelChatTurn).mockReset();
    vi.mocked(api.createChatConversation).mockResolvedValue({
      id: "conversation-new",
      mode: "general",
      context_revision: 1,
    });
    vi.mocked(api.clearChatConversation).mockResolvedValue(true);
    vi.mocked(api.chatConversationTurns).mockResolvedValue([]);
    vi.mocked(api.cancelChatTurn).mockResolvedValue({
      conversation_id: "conversation-early",
      client_message_id: "client-cancelled",
      status: "interrupted",
      state: "cancelled",
      processing_stage: "cancelled",
      attempt: 1,
      retryable: true,
      error_code: "client_cancelled",
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    cleanup();
  });

  it("mantiene el historial visible y bloquea solo la generación si el proveedor está ausente", async () => {
    sessionStorage.setItem(
      "hemovet4-chat:v1:owner-1",
      JSON.stringify({
        version: 1,
        userId: "owner-1",
        conversationId: "conversation-degraded",
        contextRevision: 1,
        scope: "general",
        contextKey: "general",
        updatedAt: "2026-08-02T12:00:00.000Z",
      }),
    );
    vi.mocked(api.chatAvailability).mockResolvedValue(chatAvailability(false));
    vi.mocked(api.chatConversationTurns).mockResolvedValueOnce([
      {
        conversation_id: "conversation-degraded",
        client_message_id: "client-existing",
        context_revision: 1,
        turn_index: 1,
        status: "completed",
        state: "completed",
        attempt: 1,
        retryable: false,
        user_message: {
          id: "user-existing",
          content: "Pregunta conservada",
          status: "completed",
        },
        response: {
          ...chatResponse(),
          conversation_id: "conversation-degraded",
          answer: "Respuesta conservada",
        },
      },
    ]);

    renderAssistantPage();

    expect(await screen.findByText("Respuesta conservada")).toBeVisible();
    expect(screen.getByText("Generación temporalmente en pausa")).toBeVisible();
    expect(screen.getByText(/conversaciones anteriores/i)).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeDisabled();
    expect(api.chatConversationTurns).toHaveBeenCalledWith("conversation-degraded");
    expect(api.createChatConversation).not.toHaveBeenCalled();
  });

  it("falla cerrado sin ocultar historial cuando no puede confirmar disponibilidad", async () => {
    vi.mocked(api.chatAvailability).mockRejectedValue(new Error("network unavailable"));

    renderAssistantPage();

    expect(await screen.findByText("Generación temporalmente en pausa")).toBeVisible();
    expect(screen.getByText(/no se pudo confirmar la disponibilidad/i)).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeDisabled();
    expect(await screen.findByRole("radio", { name: /Chat general/ })).toBeVisible();
  });

  it("sondea cada 15 segundos y recupera el composer sin borrar la conversación", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(api.chatAvailability)
      .mockResolvedValueOnce(chatAvailability(false))
      .mockResolvedValue(chatAvailability(true));

    renderAssistantPage();
    await vi.waitFor(() => expect(api.chatAvailability).toHaveBeenCalledOnce());
    expect(screen.getByText("Generación temporalmente en pausa")).toBeVisible();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(15_000);
    });
    await vi.waitFor(() => expect(api.chatAvailability).toHaveBeenCalledTimes(2));
    await vi.waitFor(() =>
      expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeEnabled(),
    );
    expect(screen.queryByText("Generación temporalmente en pausa")).not.toBeInTheDocument();
    expect(api.clearChatConversation).not.toHaveBeenCalled();
  });

  it("mantiene el núcleo navegable y bloquea generación si el RAG requerido está degradado", async () => {
    vi.mocked(api.chatAvailability).mockResolvedValue(chatAvailability(true, false));

    renderAssistantPage();

    expect(await screen.findByText("Generación temporalmente en pausa")).toBeVisible();
    expect(await screen.findByText(/fuentes veterinarias requeridas/i)).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeDisabled();
    expect(await screen.findByRole("radio", { name: /Chat general/ })).toBeVisible();
    expect(api.streamChat).not.toHaveBeenCalled();
  });

  it("expone tres modos como radios y hace visible el estudio seleccionado", async () => {
    const user = userEvent.setup();
    renderAssistantPage();

    const general = screen.getByRole("radio", { name: /Chat general/ });
    const selected = await screen.findByRole("radio", { name: /Hemograma seleccionado/ });
    const history = screen.getByRole("radio", { name: /Historial de hemogramas/ });
    expect(general).toBeChecked();

    await user.click(selected);
    expect(selected).toBeChecked();
    expect(screen.getByLabelText("Hemograma activo")).toHaveValue("analysis-july");
    expect(
      screen.getByText(/Estás viendo el hemograma de Luna del 15 de julio de 2026/i),
    ).toBeVisible();

    await user.click(history);
    expect(history).toBeChecked();
    expect(screen.queryByLabelText("Hemograma activo")).not.toBeInTheDocument();
    expect(screen.getByText("Historial de Luna")).toBeVisible();
    expect(screen.getByText("2 hemogramas disponibles para comparar.")).toBeVisible();
  });

  it("muestra sugerencias propias de cada modo y sincroniza el contexto con la URL", async () => {
    const user = userEvent.setup();
    renderAssistantPage();

    expect(
      await screen.findByRole("button", { name: "¿Qué mide un hemograma canino?" }),
    ).toBeEnabled();
    expect(
      screen.queryByRole("button", { name: "¿Qué cambió entre los estudios?" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: /Hemograma seleccionado/ }));
    expect(
      await screen.findByRole("button", { name: "¿Qué valores aparecen fuera del rango?" }),
    ).toBeEnabled();
    expect(window.location.search).toContain("scope=selected_hemogram");
    expect(window.location.search).toContain("analysis_id=analysis-july");

    await user.selectOptions(screen.getByLabelText("Hemograma activo"), "analysis-march");
    await waitFor(() => expect(window.location.search).toContain("analysis_id=analysis-march"));

    await user.click(screen.getByRole("radio", { name: /Historial de hemogramas/ }));
    expect(
      await screen.findByRole("button", { name: "¿Qué cambió entre los estudios?" }),
    ).toBeEnabled();
    expect(window.location.search).toContain("scope=hemogram_history");
    expect(window.location.search).not.toContain("analysis_id");
  });

  it("envía el historial con pet_id y sin analysis_id incompatible", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockResolvedValue(chatResponse());
    renderAssistantPage();

    await user.click(await screen.findByRole("radio", { name: /Historial de hemogramas/ }));
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué cambió entre los hemogramas?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    await waitFor(() => expect(api.streamChat).toHaveBeenCalledOnce());
    expect(vi.mocked(api.streamChat).mock.calls[0]?.[0]).toMatchObject({
      context_scope: "hemogram_history",
      pet_id: "pet-1",
      analysis_id: undefined,
    });
  });

  it("envía opciones vacías compatibles con el contrato estricto del backend", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockResolvedValue(chatResponse());
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué mide un hemograma?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    await waitFor(() => expect(api.streamChat).toHaveBeenCalledOnce());
    const payload = vi.mocked(api.streamChat).mock.calls[0]?.[0];
    expect(payload?.options).toEqual({});
    expect(payload?.options).not.toHaveProperty("thinking");
  });

  it("mantiene pet_id y analysis_id en cada turno del hemograma seleccionado", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockResolvedValue(chatResponse());
    renderAssistantPage();

    await user.click(await screen.findByRole("radio", { name: /Hemograma seleccionado/ }));
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué valor tienen los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    await waitFor(() => expect(api.streamChat).toHaveBeenCalledOnce());
    expect(vi.mocked(api.streamChat).mock.calls[0]?.[0]).toMatchObject({
      context_scope: "selected_hemogram",
      pet_id: "pet-1",
      analysis_id: "analysis-july",
    });
  });

  it("aborta una respuesta pendiente y elimina mensajes incompatibles al cambiar de contexto", async () => {
    const user = userEvent.setup();
    let signal: AbortSignal | undefined;
    vi.mocked(api.streamChat).mockImplementation(
      (_payload, options) =>
        new Promise((_resolve, reject) => {
          signal = options.signal;
          signal?.addEventListener("abort", () =>
            reject(new DOMException("Aborted", "AbortError")),
          );
        }),
    );
    renderAssistantPage();
    await screen.findByRole("radio", { name: /Historial de hemogramas/ });
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(screen.getByText("¿Qué son los leucocitos?")).toBeVisible();

    await user.click(screen.getByRole("radio", { name: /Historial de hemogramas/ }));

    expect(signal?.aborted).toBe(true);
    expect(screen.queryByText("¿Qué son los leucocitos?")).not.toBeInTheDocument();
    expect(await screen.findByText(/Chat nuevo listo en historial de Luna/i)).toBeVisible();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("muestra el evento final antes de done y conserva una sola respuesta final", async () => {
    const user = userEvent.setup();
    let resolveStream: ((response: ChatResponse) => void) | undefined;
    vi.mocked(api.streamChat).mockImplementation(
      (_payload, options) =>
        new Promise((resolve) => {
          resolveStream = resolve;
          options.onEvent({
            event: "start",
            data: { conversation_id: "conversation-early", context_revision: 4 },
          });
          options.onEvent({
            event: "generation_started",
            data: { stream_mode: "live_validated", generation_attempt: 1 },
          });
          options.onEvent({
            event: "final",
            data: { answer: "Los leucocitos son células de defensa." },
          });
        }),
    );
    const { container } = renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    expect(await screen.findByText("Los leucocitos son células de defensa.")).toBeVisible();
    expect(screen.getByText("Generando y validando una respuesta segura…")).toBeVisible();
    expect(screen.getByRole("log", { name: /Conversación/ })).toHaveAttribute("aria-busy", "true");

    resolveStream?.(chatResponse());

    await waitFor(() =>
      expect(screen.getByRole("log", { name: /Conversación/ })).toHaveAttribute(
        "aria-busy",
        "false",
      ),
    );
    expect(screen.getAllByText("Los leucocitos son células de defensa.")).toHaveLength(1);
    expect(container.querySelectorAll('.chat-message[data-role="assistant"]')).toHaveLength(1);
  });

  it("reutiliza la conversación recibida temprano si se cancela y se reintenta", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat)
      .mockImplementationOnce(
        (_payload, options) =>
          new Promise((_resolve, reject) => {
            options.onEvent({
              event: "start",
              data: {
                conversation_id: "conversation-early",
                context_revision: 7,
                attempt: 1,
              },
            });
            options.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            );
          }),
      )
      .mockResolvedValueOnce(chatResponse());
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    await user.click(screen.getByRole("button", { name: "Detener generación" }));
    const status = (await screen.findByText("Generación detenida")).closest(".chat-error");
    if (!(status instanceof HTMLElement)) throw new Error("Missing recovery status");
    await user.click(within(status).getByRole("button", { name: "Reintentar" }));

    await waitFor(() =>
      expect(api.cancelChatTurn).toHaveBeenCalledWith("conversation-early", expect.any(String), 1),
    );

    await waitFor(() => expect(api.streamChat).toHaveBeenCalledTimes(2));
    expect(vi.mocked(api.streamChat).mock.calls[1]?.[0]).toMatchObject({
      conversation_id: "conversation-early",
      expected_context_revision: 7,
    });
  });

  it("permite detener y reintentar sin convertir el error en un mensaje del asistente", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat)
      .mockImplementationOnce(
        (_payload, options) =>
          new Promise((_resolve, reject) => {
            options.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            );
          }),
      )
      .mockResolvedValueOnce(
        chatResponse([
          {
            citation_id: "S1",
            display_title: "Schalm's Veterinary Hematology",
            edition: "6.ª edición",
            section: "Leucocytosis",
            page_start: 123,
            page_end: 125,
            source_id: "schalms_pdf_pages_0101_docling",
            source_path: "/private/schalm.pdf",
            score: 0.91,
          },
        ]),
      );
    const { container } = renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    await user.click(screen.getByRole("button", { name: "Detener generación" }));

    const status = (await screen.findByText("Generación detenida")).closest(".chat-error");
    if (!(status instanceof HTMLElement)) throw new Error("Missing recovery status");
    expect(within(status).getByText(/La generación se detuvo/)).toBeVisible();
    expect(container.querySelectorAll('.chat-message[data-role="assistant"]')).toHaveLength(0);

    await user.click(within(status).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Los leucocitos son células de defensa.")).toBeVisible();
    await user.click(screen.getByText("Ver fuentes (1)"));
    expect(screen.getByText("Schalm's Veterinary Hematology, 6.ª edición")).toBeVisible();
    expect(screen.queryByText(/_pdf_pages_|private\/schalm|0\.91/)).not.toBeInTheDocument();

    const firstPayload = vi.mocked(api.streamChat).mock.calls[0]?.[0];
    const retryPayload = vi.mocked(api.streamChat).mock.calls[1]?.[0];
    expect(retryPayload?.client_message_id).toBe(firstPayload?.client_message_id);
  });

  it("restaura el transcript autorizado al recargar durante la misma sesión", async () => {
    sessionStorage.setItem(
      "hemovet4-chat:v1:owner-1",
      JSON.stringify({
        version: 1,
        userId: "owner-1",
        conversationId: "conversation-restored",
        contextRevision: 3,
        scope: "general",
        contextKey: "general",
        lastClientMessageId: "client-restored",
        updatedAt: "2026-07-17T12:00:00.000Z",
      }),
    );
    vi.mocked(api.chatConversationTurns).mockResolvedValueOnce([
      {
        conversation_id: "conversation-restored",
        client_message_id: "client-restored",
        context_revision: 3,
        turn_index: 1,
        status: "completed",
        state: "completed",
        attempt: 1,
        retryable: false,
        user_message: {
          id: "user-restored",
          content: "¿Cuál fue mi primera pregunta?",
          status: "completed",
        },
        response: {
          ...chatResponse(),
          conversation_id: "conversation-restored",
          message_id: "assistant-restored",
          client_message_id: "client-restored",
          answer: "Tu primera pregunta fue sobre los leucocitos.",
        },
      },
    ]);

    renderAssistantPage();
    await waitForChatReady();

    expect(screen.getByText("¿Cuál fue mi primera pregunta?")).toBeVisible();
    expect(screen.getByText("Tu primera pregunta fue sobre los leucocitos.")).toBeVisible();
    expect(api.chatConversationTurns).toHaveBeenCalledWith("conversation-restored");
    expect(api.clearChatConversation).not.toHaveBeenCalled();
    expect(api.createChatConversation).not.toHaveBeenCalled();
    expect(screen.getByText(/Conversación restaurada en chat general/i)).toBeVisible();
    expect(sessionStorage.getItem("hemovet4-chat:v1:owner-1")).toBeNull();
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).toContain("conversation-restored");
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).toContain("client-restored");
  });

  it("aísla los modos y restaura General al regresar dentro de la sesión", async () => {
    vi.mocked(api.createChatConversation)
      .mockResolvedValueOnce({
        id: "conversation-general-initial",
        mode: "general",
        context_revision: 1,
      })
      .mockResolvedValueOnce({
        id: "conversation-history-fresh",
        mode: "hemogram_history",
        context_revision: 1,
      });
    let responseIndex = 0;
    vi.mocked(api.streamChat).mockImplementation(async (payload) => {
      responseIndex += 1;
      const answer =
        responseIndex === 1
          ? "Respuesta general inicial"
          : responseIndex === 2
            ? "Respuesta histórica"
            : "Respuesta general nueva";
      return {
        ...chatResponse(),
        conversation_id: payload.conversation_id as string,
        message_id: `assistant-${responseIndex}`,
        answer,
        scope: payload.context_scope,
      };
    });

    renderAssistantPage();
    const user = userEvent.setup();
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "Pregunta educativa general",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(await screen.findByText("Respuesta general inicial")).toBeVisible();

    await user.click(screen.getByRole("radio", { name: /Historial de hemogramas/ }));
    expect(screen.queryByText("Respuesta general inicial")).not.toBeInTheDocument();
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "Pregunta sobre el historial",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(await screen.findByText("Respuesta histórica")).toBeVisible();

    await user.click(screen.getByRole("radio", { name: /Chat general/ }));
    expect(screen.queryByText("Respuesta histórica")).not.toBeInTheDocument();
    expect(screen.queryByText("Respuesta general inicial")).not.toBeInTheDocument();
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué es el hematocrito?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(await screen.findByText("Respuesta general nueva")).toBeVisible();

    expect(
      vi.mocked(api.streamChat).mock.calls.map(([payload]) => payload.conversation_id),
    ).toEqual([
      "conversation-general-initial",
      "conversation-history-fresh",
      "conversation-general-initial",
    ]);
    expect(api.clearChatConversation).not.toHaveBeenCalled();
    expect(api.chatConversationTurns).toHaveBeenCalledWith("conversation-general-initial");
  });

  it("conserva mensajes, input y sesión al ocultar y volver a mostrar la pestaña", async () => {
    vi.mocked(api.createChatConversation).mockResolvedValueOnce({
      id: "conversation-visible-1",
      mode: "general",
      context_revision: 1,
    });
    vi.mocked(api.streamChat).mockImplementation(async (payload) => {
      return {
        ...chatResponse(),
        conversation_id: payload.conversation_id as string,
        message_id: "assistant-visible-1",
        answer: "Respuesta antes de ocultar",
      };
    });

    renderAssistantPage();
    const user = userEvent.setup();
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "Pregunta inicial",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(await screen.findByText("Respuesta antes de ocultar")).toBeVisible();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "borrador que debe permanecer",
    );

    let visibilityState: DocumentVisibilityState = "visible";
    const visibilitySpy = vi
      .spyOn(document, "visibilityState", "get")
      .mockImplementation(() => visibilityState);
    vi.mocked(api.clearChatConversation).mockClear();
    visibilityState = "hidden";
    act(() => document.dispatchEvent(new Event("visibilitychange")));

    expect(screen.getByText("Respuesta antes de ocultar")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toHaveValue(
      "borrador que debe permanecer",
    );
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).toContain("conversation-visible-1");
    expect(api.clearChatConversation).not.toHaveBeenCalled();
    expect(api.createChatConversation).toHaveBeenCalledOnce();

    visibilityState = "visible";
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(screen.getByText("Respuesta antes de ocultar")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toHaveValue(
      "borrador que debe permanecer",
    );
    expect(api.clearChatConversation).not.toHaveBeenCalled();
    expect(api.createChatConversation).toHaveBeenCalledOnce();
    visibilitySpy.mockRestore();
  });

  it("pagehide conserva conversación y borrador durante la sesión del navegador", async () => {
    vi.mocked(api.createChatConversation)
      .mockResolvedValueOnce({
        id: "conversation-page-1",
        mode: "general",
        context_revision: 1,
      })
      .mockResolvedValueOnce({
        id: "conversation-page-2",
        mode: "general",
        context_revision: 1,
      });
    vi.mocked(api.streamChat).mockImplementation(async (payload) => ({
      ...chatResponse(),
      conversation_id: payload.conversation_id as string,
      answer: "Respuesta previa a navegar",
    }));

    renderAssistantPage();
    const user = userEvent.setup();
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "Pregunta antes de navegar",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(await screen.findByText("Respuesta previa a navegar")).toBeVisible();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "otro borrador",
    );

    vi.mocked(api.clearChatConversation).mockClear();
    act(() => window.dispatchEvent(new Event("pagehide")));

    expect(screen.getByText("Respuesta previa a navegar")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toHaveValue(
      "otro borrador",
    );
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).toContain("conversation-page-1");
    expect(api.clearChatConversation).not.toHaveBeenCalled();

    act(() => window.dispatchEvent(new Event("pageshow")));
    await waitForChatReady();
    expect(api.createChatConversation).toHaveBeenCalledOnce();
    expect(screen.getByText("Respuesta previa a navegar")).toBeVisible();
  });

  it("al desmontar aborta el stream y conserva el manifiesto de sesión", async () => {
    let streamSignal: AbortSignal | undefined;
    vi.mocked(api.streamChat).mockImplementationOnce(
      (_payload, options) =>
        new Promise((_resolve, reject) => {
          streamSignal = options.signal;
          options.onEvent({
            event: "start",
            data: {
              conversation_id: "conversation-unmount",
              context_revision: 2,
              attempt: 1,
            },
          });
          options.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );

    const { unmount } = renderAssistantPage();
    const user = userEvent.setup();
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "Pregunta pendiente al navegar",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    await waitFor(() => expect(api.streamChat).toHaveBeenCalledOnce());
    vi.mocked(api.clearChatConversation).mockClear();
    vi.mocked(api.cancelChatTurn).mockClear();

    unmount();

    expect(streamSignal?.aborted).toBe(true);
    expect(api.clearChatConversation).not.toHaveBeenCalled();
    expect(api.cancelChatTurn).not.toHaveBeenCalled();
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).toContain("conversation-unmount");
  });

  it("termina con una única sesión vigente bajo el replay de efectos de StrictMode", async () => {
    let createdCount = 0;
    vi.mocked(api.createChatConversation).mockImplementation(async () => {
      createdCount += 1;
      return {
        id: `conversation-strict-${createdCount}`,
        mode: "general",
        context_revision: 1,
      };
    });
    vi.mocked(api.streamChat).mockImplementation(async (payload) => ({
      ...chatResponse(),
      conversation_id: payload.conversation_id as string,
      answer: "Respuesta desde la sesión vigente",
    }));

    renderAssistantPage({ strict: true });
    const user = userEvent.setup();
    await waitForChatReady();
    expect(api.createChatConversation).toHaveBeenCalledTimes(2);
    expect(api.clearChatConversation).toHaveBeenCalledWith("conversation-strict-1");

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué mide un hemograma?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(await screen.findByText("Respuesta desde la sesión vigente")).toBeVisible();
    expect(vi.mocked(api.streamChat).mock.calls[0]?.[0].conversation_id).toBe(
      "conversation-strict-2",
    );
  });

  it("ofrece reintentar, no consultar un turno inexistente, ante un fallo de conexión temprano", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockRejectedValueOnce(new ApiError("No hay conexión"));
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué es el hematocrito?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByRole("button", { name: "Reintentar" })).toBeVisible();
    expect(within(alert).queryByRole("button", { name: "Consultar estado" })).toBeNull();
    expect(screen.getByText("¿Qué es el hematocrito?")).toBeVisible();
  });

  it("deja de sondear cuando el backend confirma un estado terminal", async () => {
    vi.mocked(api.streamChat).mockImplementationOnce((_payload, options) => {
      options.onEvent({
        event: "start",
        data: { conversation_id: "conversation-terminal", context_revision: 2 },
      });
      return Promise.reject(new ApiError("El stream terminó antes de confirmar el resultado."));
    });
    vi.mocked(api.chatTurnStatus)
      .mockResolvedValueOnce({
        conversation_id: "conversation-terminal",
        client_message_id: "client-terminal",
        status: "processing",
        state: "generating",
        processing_stage: "generating",
        attempt: 1,
        retryable: false,
      })
      .mockResolvedValueOnce({
        conversation_id: "conversation-terminal",
        client_message_id: "client-terminal",
        status: "failed",
        state: "failed_terminal",
        processing_stage: "failed_terminal",
        attempt: 1,
        retryable: false,
        error_code: "unsafe_output",
      });

    renderAssistantPage();
    const user = userEvent.setup();
    await waitForChatReady();
    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "Pregunta pendiente",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    const alert = await screen.findByRole("alert");
    await user.click(within(alert).getByRole("button", { name: "Consultar estado" }));

    expect(
      await screen.findByText("El turno terminó sin una respuesta recuperable."),
    ).toBeVisible();
    const terminalAlert = screen.getByRole("alert");
    expect(within(terminalAlert).queryByRole("button", { name: "Consultar estado" })).toBeNull();
    expect(within(terminalAlert).queryByRole("button", { name: "Reintentar" })).toBeNull();
  });

  it("reintenta el mismo turno después de un fallo canónico del backend", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat)
      .mockImplementationOnce((_payload, options) => {
        options.onEvent({
          event: "start",
          data: { conversation_id: "conversation-retry", context_revision: 1 },
        });
        return Promise.reject(
          new ApiError("La salida fue inválida.", 502, {
            code: "invalid_output_empty_output",
            message: "La salida fue inválida.",
            retryable: true,
            recovery_action: "retry_same_turn",
            request_id: "request-1",
            conversation_id: "conversation-retry",
            http_status: 502,
          }),
        );
      })
      .mockResolvedValueOnce(chatResponse());
    vi.mocked(api.chatTurnStatus).mockResolvedValue({
      conversation_id: "conversation-retry",
      client_message_id: "server-does-not-replace-client-id",
      status: "failed",
      attempt: 1,
      retryable: true,
      error_code: "invalid_output_empty_output",
    });
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("La salida fue inválida.")).toBeVisible();
    await user.click(within(alert).getByRole("button", { name: "Reintentar" }));

    await waitFor(() => expect(api.streamChat).toHaveBeenCalledTimes(2));
    const first = vi.mocked(api.streamChat).mock.calls[0]?.[0];
    const retry = vi.mocked(api.streamChat).mock.calls[1]?.[0];
    expect(retry?.client_message_id).toBe(first?.client_message_id);
    expect(retry?.conversation_id).toBe("conversation-retry");
  });

  it("recupera la respuesta canónica si el stream falla después de completarse", async () => {
    const user = userEvent.setup();
    const recovered = chatResponse();
    recovered.conversation_id = "conversation-recovered";
    vi.mocked(api.streamChat).mockImplementationOnce((_payload, options) => {
      options.onEvent({
        event: "start",
        data: { conversation_id: "conversation-recovered", context_revision: 2 },
      });
      return Promise.reject(
        new ApiError("El stream terminó incompleto.", undefined, {
          code: "stream_incomplete",
        }),
      );
    });
    vi.mocked(api.chatTurnStatus).mockResolvedValue({
      conversation_id: "conversation-recovered",
      client_message_id: "client-1",
      status: "completed",
      attempt: 1,
      retryable: false,
      response: recovered,
    });
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    expect(await screen.findByText(recovered.answer)).toBeVisible();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(api.chatTurnStatus).toHaveBeenCalledOnce();
  });

  it("limpia la conversación mediante el endpoint disponible y mantiene el contexto", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockResolvedValue(chatResponse());
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));
    expect(await screen.findByText("Los leucocitos son células de defensa.")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Limpiar" }));
    await waitFor(() => expect(api.clearChatConversation).toHaveBeenCalledWith("conversation-1"));
    expect(screen.queryByText("Los leucocitos son células de defensa.")).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Chat general/ })).toBeChecked();
  });

  it("muestra únicamente la evidencia pública compacta y una advertencia", async () => {
    const user = userEvent.setup();
    const response = chatResponse();
    response.case_facts = [{ parameter: "WBC", value: "10.4" }];
    response.warnings = ["La respuesta es educativa y no sustituye una evaluación veterinaria"];
    vi.mocked(api.streamChat).mockResolvedValue(response);
    const { container } = renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Cuál es el valor de los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    const facts = await screen.findByText("Datos utilizados");
    const block = facts.closest(".case-facts");
    expect(block?.querySelector("dl")).not.toBeNull();
    expect(within(block as HTMLElement).getByText("WBC")).toBeVisible();
    expect(within(block as HTMLElement).getByText("10.4")).toBeVisible();
    expect(
      screen.queryByText(/system_default_legacy|rango de referencia|x10³\/µL/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getAllByText("La respuesta es educativa y no sustituye una evaluación veterinaria"),
    ).toHaveLength(1);
    expect(container.querySelectorAll(".case-facts dl > div")).toHaveLength(1);
  });

  it("presenta hechos longitudinales con fecha, unidad, estado y rango", async () => {
    const user = userEvent.setup();
    const response = chatResponse();
    response.case_facts = [
      {
        parameter: "WBC",
        value: "18.77",
        unit: "×10⁹/L",
        status: "high",
        study_key: "H2",
        study_date: "2026-07-15T12:00:00Z",
        reference_min: 6,
        reference_max: 17,
      },
    ];
    vi.mocked(api.streamChat).mockResolvedValue(response);
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Cuál es el valor de los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    const facts = (await screen.findByText("Datos utilizados")).closest(".case-facts");
    if (!(facts instanceof HTMLElement)) throw new Error("Missing facts block");
    expect(within(facts).getByText("18.77 ×10⁹/L")).toBeVisible();
    expect(
      within(facts).getByText(/H2 · 15 jul(?: de)? 2026 · Alto · Rango: 6–17 ×10⁹\/L/),
    ).toBeVisible();
  });

  it("sondea el turno transitorio tras recargar durante la generación", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    sessionStorage.setItem(
      "hemovet4-chat:v1:owner-1",
      JSON.stringify({
        version: 1,
        userId: "owner-1",
        conversationId: "conversation-generating",
        contextRevision: 2,
        scope: "general",
        contextKey: "general",
        lastClientMessageId: "client-generating",
        updatedAt: "2026-08-05T12:00:00.000Z",
      }),
    );
    vi.mocked(api.chatConversationTurns).mockResolvedValueOnce([
      {
        conversation_id: "conversation-generating",
        client_message_id: "client-generating",
        context_revision: 2,
        turn_index: 1,
        status: "processing",
        state: "generating",
        processing_stage: "generating",
        attempt: 1,
        // El backend fija retryable=false mientras el turno sigue vivo.
        retryable: false,
        user_message: {
          id: "user-generating",
          content: "¿Qué son los leucocitos?",
          status: "processing",
        },
      },
    ]);
    vi.mocked(api.chatTurnStatus).mockResolvedValue({
      conversation_id: "conversation-generating",
      client_message_id: "client-generating",
      status: "completed",
      state: "completed",
      attempt: 1,
      retryable: false,
      response: {
        ...chatResponse(),
        conversation_id: "conversation-generating",
        message_id: "assistant-generating",
        answer: "Respuesta recuperada tras la recarga.",
      },
    });

    renderAssistantPage();

    await vi.waitFor(() =>
      expect(screen.getByRole("button", { name: "Consultar estado" })).toBeVisible(),
    );
    expect(screen.getByText("¿Qué son los leucocitos?")).toBeVisible();
    expect(api.createChatConversation).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3_000);
    });

    await vi.waitFor(() =>
      expect(screen.getByText("Respuesta recuperada tras la recarga.")).toBeVisible(),
    );
    expect(api.chatTurnStatus).toHaveBeenCalledWith("conversation-generating", "client-generating");
  });

  it("reutiliza la conversación activa del backend cuando la pestaña no tiene manifiesto", async () => {
    vi.mocked(api.listChatConversations).mockResolvedValue([
      {
        id: "conversation-historial",
        mode: "hemogram_history",
        pet_id: "pet-1",
        context_revision: 2,
      },
      { id: "conversation-otra-pestana", mode: "general", context_revision: 4 },
    ]);
    vi.mocked(api.chatConversationTurns).mockResolvedValueOnce([
      {
        conversation_id: "conversation-otra-pestana",
        client_message_id: "client-otra-pestana",
        context_revision: 4,
        turn_index: 1,
        status: "completed",
        state: "completed",
        attempt: 1,
        retryable: false,
        user_message: {
          id: "user-otra-pestana",
          content: "Pregunta hecha en otra pestaña",
          status: "completed",
        },
        response: {
          ...chatResponse(),
          conversation_id: "conversation-otra-pestana",
          message_id: "assistant-otra-pestana",
          answer: "Respuesta hecha en otra pestaña",
        },
      },
    ]);

    renderAssistantPage();

    expect(await screen.findByText("Respuesta hecha en otra pestaña")).toBeVisible();
    expect(api.chatConversationTurns).toHaveBeenCalledWith("conversation-otra-pestana");
    expect(api.createChatConversation).not.toHaveBeenCalled();
  });

  it("tolera un fallo aislado de disponibilidad y solo pausa tras dos consecutivos", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(api.chatAvailability)
      .mockResolvedValueOnce(chatAvailability())
      .mockRejectedValue(new Error("probe timeout"));

    renderAssistantPage();
    await vi.waitFor(() =>
      expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeEnabled(),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CHAT_AVAILABILITY_POLL_MS);
    });
    await vi.waitFor(() => expect(api.chatAvailability).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeEnabled();
    expect(screen.queryByText("Generación temporalmente en pausa")).not.toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(CHAT_AVAILABILITY_POLL_MS);
    });
    await vi.waitFor(() => expect(api.chatAvailability).toHaveBeenCalledTimes(3));
    await vi.waitFor(() =>
      expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeDisabled(),
    );
    expect(screen.getByText("Generación temporalmente en pausa")).toBeVisible();
  });

  it("explica en lenguaje llano una respuesta que no superó la reparación", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockImplementationOnce((_payload, options) => {
      options.onEvent({
        event: "start",
        data: { conversation_id: "conversation-repair", context_revision: 1 },
      });
      return Promise.reject(
        new ApiError(
          "La reparación no cumplió el contrato estructurado y no se mostró contenido.",
          502,
          {
            code: "generation_repair_failed",
            message: "La reparación no cumplió el contrato estructurado y no se mostró contenido.",
            category: "validation",
            retryable: true,
            recovery_action: "retry_same_turn",
            request_id: "request-repair",
            conversation_id: "conversation-repair",
            retry_after_ms: 0,
            http_status: 502,
          },
        ),
      );
    });
    vi.mocked(api.chatTurnStatus).mockResolvedValue({
      conversation_id: "conversation-repair",
      client_message_id: "client-repair",
      status: "failed",
      state: "failed_retryable",
      attempt: 1,
      retryable: true,
      error_code: "generation_repair_failed",
    });
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText(/no pasó las comprobaciones de seguridad/i)).toBeVisible();
    expect(within(alert).queryByText(/contrato estructurado/i)).toBeNull();
    expect(within(alert).getByRole("button", { name: "Reintentar" })).toBeEnabled();
  });

  it("respeta retry_after_ms cuando el asistente está ocupado con otra consulta", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockImplementationOnce((_payload, options) => {
      options.onEvent({
        event: "start",
        data: { conversation_id: "conversation-queue", context_revision: 1 },
      });
      return Promise.reject(
        new ApiError(
          "El asistente está atendiendo otra solicitud. Puedes reintentar esta misma pregunta.",
          429,
          {
            code: "generation_queue_timeout",
            message:
              "El asistente está atendiendo otra solicitud. Puedes reintentar esta misma pregunta.",
            category: "capacity",
            retryable: true,
            recovery_action: "retry_same_turn",
            request_id: "request-queue",
            conversation_id: "conversation-queue",
            retry_after_ms: 2000,
            http_status: 429,
          },
        ),
      );
    });
    vi.mocked(api.chatTurnStatus).mockResolvedValue({
      conversation_id: "conversation-queue",
      client_message_id: "client-queue",
      status: "failed",
      state: "failed_retryable",
      attempt: 1,
      retryable: true,
      error_code: "generation_queue_timeout",
    });
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "¿Qué son los leucocitos?",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText(/ocupado con otra consulta/i)).toBeVisible();
    const retry = within(alert).getByRole("button", { name: /Reintentar/ });
    expect(retry).toBeDisabled();
    expect(retry).toHaveTextContent(/Reintentar en [12] s/);
  });

  it("sugiere acotar la pregunta cuando el contexto clínico no cabe", async () => {
    const user = userEvent.setup();
    vi.mocked(api.streamChat).mockRejectedValueOnce(
      new ApiError("La evidencia imprescindible no cabe de forma segura.", 422, {
        code: "context_budget_exceeded",
        message: "La evidencia imprescindible no cabe de forma segura en el contexto del modelo.",
        category: "validation",
        retryable: false,
        recovery_action: "start_new_conversation",
        request_id: "request-budget",
        conversation_id: "conversation-budget",
        retry_after_ms: 0,
        http_status: 422,
      }),
    );
    renderAssistantPage();
    await waitForChatReady();

    await user.type(
      screen.getByRole("textbox", { name: "Pregunta para el asistente" }),
      "Explícame todo el historial completo",
    );
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText(/pregunta más específica/i)).toBeVisible();
    expect(within(alert).queryByRole("button", { name: "Iniciar chat compatible" })).toBeNull();
    expect(within(alert).queryByRole("button", { name: /Reintentar/ })).toBeNull();
    expect(api.chatTurnStatus).not.toHaveBeenCalled();
    // El texto sigue editable para reformular la pregunta sin perder el chat.
    expect(screen.getByRole("textbox", { name: "Pregunta para el asistente" })).toBeEnabled();
  });

  it("muestra el tiempo transcurrido del heartbeat sin bloquear el cuadro de texto", async () => {
    const user = userEvent.setup();
    let resolveStream: ((response: ChatResponse) => void) | undefined;
    vi.mocked(api.streamChat).mockImplementation(
      (_payload, options) =>
        new Promise((resolve) => {
          resolveStream = resolve;
          options.onEvent({
            event: "generation_started",
            data: { stream_mode: "live_validated", generation_attempt: 1 },
          });
          options.onEvent({
            event: "heartbeat",
            data: { stage: "generating", elapsed_ms: 47_000 },
          });
        }),
    );
    renderAssistantPage();
    await waitForChatReady();

    const composer = screen.getByRole("textbox", { name: "Pregunta para el asistente" });
    await user.type(composer, "¿Qué son los leucocitos?");
    await user.click(screen.getByRole("button", { name: "Enviar pregunta" }));

    expect(
      await screen.findByText(/Generando y validando una respuesta segura… · 47 s/),
    ).toBeVisible();
    expect(composer).toBeEnabled();

    resolveStream?.(chatResponse());
    expect(await screen.findByText("Los leucocitos son células de defensa.")).toBeVisible();
  });

  it("crea un nuevo chat remoto con el contexto canónico activo", async () => {
    const user = userEvent.setup();
    renderAssistantPage();
    await waitForChatReady();
    vi.mocked(api.createChatConversation).mockClear();

    await user.click(screen.getByRole("button", { name: "Nuevo chat" }));

    await waitFor(() =>
      expect(api.createChatConversation).toHaveBeenCalledWith({
        context_scope: "general",
        analysis_id: undefined,
        pet_id: undefined,
      }),
    );
    expect(api.createChatConversation).toHaveBeenCalledOnce();
    expect(screen.getByText("Nuevo chat listo en chat general.")).toBeVisible();
  });
});
