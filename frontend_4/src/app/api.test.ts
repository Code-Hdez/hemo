import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatRequestPayload, ChatResponse } from "../domain/types";
import { api, mapAnalysis, mapPet, setUnauthorizedHandler } from "./api";

const chatPayload = {
  client_message_id: "8dcb9d86-3053-4fae-99a5-078642242d1d",
  conversation_id: null,
  message: "¿Qué son las plaquetas?",
  context_scope: "general" as const,
  analysis_id: undefined,
  options: {},
} satisfies ChatRequestPayload;

function finalChatResponse(overrides: Partial<ChatResponse> = {}): ChatResponse {
  return {
    conversation_id: "conversation-1",
    message_id: "message-1",
    answer: "Respuesta educativa.",
    scope: "general",
    case_facts: [],
    sources: [],
    warnings: [],
    safety_action: "allow",
    model: "qwen3:4b",
    usage: { prompt_tokens: 20, completion_tokens: 5 },
    duration_ms: 15,
    finish_reason: "stop",
    llm_invoked: true,
    response_origin: "llm",
    attempt: 1,
    generation_attempts: 1,
    stream_mode: "buffered_validated",
    validation_status: "passed",
    ...overrides,
  };
}

beforeEach(() => {
  sessionStorage.clear();
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
  });
});

afterEach(() => {
  setUnauthorizedHandler();
  vi.unstubAllGlobals();
});

describe("mappers de API", () => {
  it("tolera los campos opcionales que devuelve una mascota real", () => {
    const pet = mapPet({
      id: "pet-1",
      owner_id: "owner-1",
      name: "Luna",
      breed: null,
      birth_year: null,
      sex: null,
      weight_kg: null,
      notes: null,
      residence_consent: false,
      created_at: "2026-06-20T10:00:00Z",
    });

    expect(pet.residence_consent).toBe(false);
    expect(pet.image).toBeUndefined();
  });

  it("adapta la URL opaca de una foto del backend al avatar de la interfaz", () => {
    const pet = mapPet({
      id: "pet-1",
      owner_id: "owner-1",
      name: "Luna",
      residence_consent: true,
      created_at: "2026-06-20T10:00:00Z",
      photo_url: "/api/v1/media/pets/4fd0e9050bd143b08b8ac27cdb9a6aaa.webp",
    });

    expect(pet.image).toContain("/api/v1/media/pets/4fd0e9050bd143b08b8ac27cdb9a6aaa.webp");
  });

  it("asigna un enlace de biblioteca solo cuando encuentra una coincidencia real", () => {
    const analysis = mapAnalysis({
      id: "analysis-1",
      status: "success",
      imputed_fields: [],
      extraction_warnings: [],
      filename: "sample.pdf",
      file_size: 1,
      created_at: "2026-06-20T10:00:00Z",
      confidence: 0.8,
      quality_score: 0.9,
      species: "Canina",
      summary: "Resumen",
      diagnoses: [],
      findings: [
        { label: "Patrón inflamatorio", detail: "Detalle", severity: "warn" },
        { label: "Hallazgo sin glosario", detail: "Detalle", severity: "info" },
      ],
      qc_flags: [],
      lab_values: [],
      persisted: true,
    });

    expect(analysis.findings[0]?.glossary_slug).toBe("patron-inflamatorio");
    expect(analysis.findings[1]?.glossary_slug).toBeUndefined();
  });
});

describe("disponibilidad del chat", () => {
  it("consulta el contrato versionado sin depender de la dirección del proveedor", async () => {
    localStorage.setItem("hemovet4-token", "active-token");
    const payload = {
      contract_version: "hemovet.availability/v1",
      probe: "chat_availability",
      status: "degraded",
      chat_ready: false,
      module_ready: true,
      provider_ready: false,
      llm_ready: false,
      rag_required: true,
      rag_ready: true,
      chroma_ready: true,
      collection_ready: true,
      codes: ["LLM_PROVIDER_UNAVAILABLE"],
      provider: {
        contract_version: "hemovet.availability/v1",
        probe: "provider_availability",
        status: "unavailable",
        provider: "remote",
        model: "qwen3:4b",
        ready: false,
        code: "LLM_PROVIDER_UNAVAILABLE",
        retryable: true,
        identity_verified: null,
      },
      rag: {
        contract_version: "hemovet.availability/v1",
        probe: "rag_availability",
        status: "ready",
        required: true,
        ready: true,
        chroma_ready: true,
        collection_ready: true,
        index_ready: true,
        codes: [],
      },
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await api.chatAvailability();

    expect(result.chat_ready).toBe(false);
    expect(result.provider.code).toBe("LLM_PROVIDER_UNAVAILABLE");
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/chat/health");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer active-token");
    expect(url).not.toContain("11434");
  });
});

describe("atención veterinaria cercana", () => {
  it("envía mascota y radio al endpoint autenticado del mapa", async () => {
    localStorage.setItem("hemovet4-token", "active-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [],
          source: "openstreetmap",
          search_url: "https://www.openstreetmap.org/search?query=veterinaria",
          location_precision: "grid_2km",
          message: "Sin centros confirmados.",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.nearbyVeterinaryCare({
      pet_id: "pet-1",
      radius_meters: 25_000,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/v1/residence/nearby-veterinary-care");
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer active-token");
    expect(JSON.parse(String(init.body))).toEqual({
      pet_id: "pet-1",
      radius_meters: 25_000,
    });
  });
});

describe("payloads de análisis", () => {
  it("permite analizar valores confirmados sin pet_id y no serializa undefined", async () => {
    localStorage.setItem("hemovet4-token", "stale-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "tmp-1",
          status: "partial_imputation",
          imputed_fields: [],
          extraction_warnings: [],
          filename: "temporal.pdf",
          file_size: 100,
          created_at: "2026-06-25T12:00:00Z",
          confidence: 0.7,
          quality_score: 0.8,
          species: "Canina",
          summary: "Resultado temporal.",
          diagnoses: ["Resultado temporal"],
          findings: [],
          qc_flags: [],
          lab_values: [],
          persisted: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.analyzeConfirmed({
      cbc: { WBC: 12.4, RBC: 6.2, HGB: 14.1 },
      metadata: {},
      comments: null,
      extraction_provider: "gemini",
      extraction_mode: "auto",
      extraction_warnings: [],
      filename: "temporal.pdf",
      file_size: 100,
    });

    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(body.pet_id).toBeUndefined();
    expect(JSON.stringify(body)).not.toContain("undefined");
    expect(init.credentials).toBe("omit");
    expect(new Headers(init.headers).has("Authorization")).toBe(false);
  });

  it("extrae hemogramas sin enviar sesión para soportar modo invitado", async () => {
    localStorage.setItem("hemovet4-token", "stale-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          cbc: { WBC: 12.4, RBC: 6.2, HGB: 14.1 },
          metadata: { species: "Canino" },
          comments: null,
          extraction_provider: "gemini",
          extraction_mode: "auto",
          fallback_used: false,
          warnings: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.extract(new File(["hemograma"], "hemograma.png", { type: "image/png" }));

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.credentials).toBe("omit");
    expect(new Headers(init.headers).has("Authorization")).toBe(false);
  });

  it("mantiene autorización cuando el análisis confirmado se asocia a una mascota", async () => {
    localStorage.setItem("hemovet4-token", "active-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "analysis-1",
          status: "success",
          imputed_fields: [],
          extraction_warnings: [],
          filename: "temporal.pdf",
          file_size: 100,
          created_at: "2026-06-25T12:00:00Z",
          confidence: 0.7,
          quality_score: 0.8,
          species: "Canina",
          summary: "Resultado guardado.",
          diagnoses: ["Resultado"],
          findings: [],
          qc_flags: [],
          lab_values: [],
          persisted: true,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.analyzeConfirmed({
      cbc: { WBC: 12.4, RBC: 6.2, HGB: 14.1 },
      metadata: {},
      comments: null,
      extraction_provider: "gemini",
      extraction_mode: "auto",
      extraction_warnings: [],
      filename: "temporal.pdf",
      file_size: 100,
      pet_id: "pet-1",
    });

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(init.credentials).toBe("include");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer active-token");
  });
});

describe("autenticación del stream de chat", () => {
  it("conserva código, estado HTTP y acción de recuperación de un error SSE", async () => {
    const error = {
      code: "provider_timeout",
      message: "El modelo tardó demasiado.",
      detail: "El proveedor agotó el tiempo permitido sin confirmar una respuesta.",
      category: "timeout",
      retryable: true,
      recovery_action: "retry_same_turn",
      request_id: "request-1",
      client_message_id: chatPayload.client_message_id,
      conversation_id: "conversation-1",
      attempt: 1,
      retry_after_ms: 1000,
      http_status: 504,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(`event: error\ndata: ${JSON.stringify(error)}\n\n`, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      ),
    );

    await expect(api.streamChat(chatPayload, { onEvent: vi.fn() })).rejects.toMatchObject({
      status: 504,
      detail: error,
    });
  });

  it("propaga el evento final con texto limpio y devuelve la respuesta final", async () => {
    const finalResponse = finalChatResponse({
      answer: "Respuesta educativa [S1].",
      warnings: ["Advertencia"],
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        new Response(
          [
            'event: generation_started\ndata: {"stream_mode":"live_validated","generation_attempt":1}\n\n',
            `event: final\ndata: ${JSON.stringify(finalResponse)}\n\n`,
            `event: done\ndata: ${JSON.stringify(finalResponse)}\n\n`,
          ].join(""),
          { status: 200, headers: { "Content-Type": "text/event-stream" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const onEvent = vi.fn();

    const response = await api.streamChat(chatPayload, { onEvent });

    expect(response).toEqual({ ...finalResponse, answer: "Respuesta educativa." });
    expect(onEvent).toHaveBeenCalledWith({
      event: "final",
      data: { ...finalResponse, answer: "Respuesta educativa." },
    });
    const requestHeaders = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
    expect(requestHeaders.get("X-HemoVet-Browser-Session-ID")).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it("entrega start y el evento final antes de que termine el turno", async () => {
    const encoder = new TextEncoder();
    let streamController: ReadableStreamDefaultController<Uint8Array> | undefined;
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        streamController = controller;
      },
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream; charset=utf-8" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const onEvent = vi.fn();
    let settled = false;

    const responsePromise = api.streamChat(chatPayload, { onEvent }).finally(() => {
      settled = true;
    });
    streamController?.enqueue(
      encoder.encode('event: start\ndata: {"conversation_id":"conversation-1","revision":3}\n\n'),
    );

    await vi.waitFor(() => {
      expect(onEvent).toHaveBeenCalledWith({
        event: "start",
        data: {
          conversation_id: "conversation-1",
          revision: 3,
          context_revision: 3,
        },
      });
    });
    expect(settled).toBe(false);

    const finalResponse = finalChatResponse({
      answer: "Los leucocitos.",
      model: "qwen",
      usage: { prompt_tokens: 10, completion_tokens: 3 },
      duration_ms: 20,
      context: { context_revision: 3 },
    });
    streamController?.enqueue(
      encoder.encode(`event: final\ndata: ${JSON.stringify(finalResponse)}\n\n`),
    );

    await vi.waitFor(() => {
      expect(onEvent).toHaveBeenCalledWith({ event: "final", data: finalResponse });
    });
    expect(settled).toBe(false);

    streamController?.enqueue(
      encoder.encode(`event: done\ndata: ${JSON.stringify(finalResponse)}\n\n`),
    );
    streamController?.close();

    await expect(responsePromise).resolves.toEqual(finalResponse);
    expect(onEvent.mock.calls.filter(([event]) => event.event === "final")).toHaveLength(1);
    const requestHeaders = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
    expect(requestHeaders.get("Accept")).toBe("text/event-stream");
    expect(requestHeaders.get("Cache-Control")).toBe("no-cache");
  });

  it("procesa un done sin separador final y descarta eventos finales numerados repetidos", async () => {
    const finalResponse = finalChatResponse({
      answer: "Respuesta única.",
      model: "qwen",
      usage: { prompt_tokens: 10, completion_tokens: 2 },
      duration_ms: 12,
    });
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            `event: final\ndata: ${JSON.stringify({ ...finalResponse, sequence: 4 })}\n\n` +
              `event: final\ndata: ${JSON.stringify({ ...finalResponse, sequence: 4 })}\n\n` +
              `event: done\ndata: ${JSON.stringify(finalResponse)}`,
            { status: 200, headers: { "Content-Type": "text/event-stream" } },
          ),
        ),
    );
    const onEvent = vi.fn();

    await expect(api.streamChat(chatPayload, { onEvent })).resolves.toEqual(finalResponse);
    expect(onEvent.mock.calls.filter(([event]) => event.event === "final")).toHaveLength(1);
  });

  it("rechaza un duplicado de secuencia con contenido conflictivo", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            'event: final\ndata: {"sequence":1,"answer":"Primero"}\n\n' +
              'event: final\ndata: {"sequence":1,"answer":"Distinto"}\n\n',
            { status: 200, headers: { "Content-Type": "text/event-stream" } },
          ),
        ),
    );

    await expect(api.streamChat(chatPayload, { onEvent: vi.fn() })).rejects.toMatchObject({
      detail: { code: "stream_sequence_conflict" },
    });
  });

  it("rechaza gaps e identidades de turno cruzadas antes de exponer contenido", async () => {
    const streams = [
      'event: status\ndata: {"sequence":1,"stage":"retrieving"}\n\n' +
        'event: status\ndata: {"sequence":3,"stage":"validating"}\n\n',
      `event: start\ndata: {"client_message_id":"otro-turno","conversation_id":"conversation-1"}\n\n`,
    ];
    const fetchMock = vi.fn().mockImplementation(
      async () =>
        new Response(streams.shift(), {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.streamChat(chatPayload, { onEvent: vi.fn() })).rejects.toMatchObject({
      detail: { code: "stream_sequence_gap" },
    });
    const onEvent = vi.fn();
    await expect(api.streamChat(chatPayload, { onEvent })).rejects.toMatchObject({
      detail: { code: "stream_client_message_mismatch" },
    });
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("clasifica un EOF sin done como interrupción SSE reanudable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          'event: start\ndata: {"request_id":"request-stream","conversation_id":"conversation-1","client_message_id":"8dcb9d86-3053-4fae-99a5-078642242d1d","attempt":3,"context_revision":2}\n\n' +
            'event: final\ndata: {"sequence":1,"answer":"Respuesta parcial"}\n\n',
          {
            status: 200,
            headers: {
              "Content-Type": "text/event-stream",
              "X-Request-ID": "request-stream",
            },
          },
        ),
      ),
    );

    await expect(api.streamChat(chatPayload, { onEvent: vi.fn() })).rejects.toMatchObject({
      detail: {
        code: "sse_connection_interrupted",
        category: "transport",
        retryable: true,
        recovery_action: "poll_turn",
        request_id: "request-stream",
        client_message_id: chatPayload.client_message_id,
        conversation_id: "conversation-1",
        http_status: 0,
      },
    });
  });

  it("recupera turnos canónicos y cancela únicamente el intento activo", async () => {
    const turn = {
      conversation_id: "conversation-1",
      client_message_id: chatPayload.client_message_id,
      context_revision: 2,
      turn_index: 1,
      status: "interrupted",
      attempt: 3,
      retryable: true,
      error_code: "client_disconnected",
      user_message: {
        id: "user-message-1",
        content: chatPayload.message,
        status: "interrupted",
      },
      response: null,
      updated_at: "2026-07-17T12:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [turn], limit: 100, offset: 0 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            conversation_id: "conversation-1",
            client_message_id: chatPayload.client_message_id,
            status: "interrupted",
            attempt: 3,
            retryable: true,
            error_code: "client_cancelled",
            response: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.chatConversationTurns("conversation-1")).resolves.toEqual([turn]);
    await expect(
      api.cancelChatTurn("conversation-1", chatPayload.client_message_id, 3),
    ).resolves.toMatchObject({ error_code: "client_cancelled", retryable: true });

    expect(fetchMock.mock.calls[0]?.[0]).toBe(
      "/api/v1/chat/conversations/conversation-1/turns?limit=100&offset=0",
    );
    expect(fetchMock.mock.calls[1]?.[0]).toBe(
      `/api/v1/chat/conversations/conversation-1/turns/${chatPayload.client_message_id}/cancel`,
    );
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({
      method: "POST",
      body: JSON.stringify({ attempt: 3 }),
    });
  });

  it("cancela el reader y rechaza con AbortError al detener el stream", async () => {
    let cancelled = false;
    const body = new ReadableStream<Uint8Array>({
      cancel() {
        cancelled = true;
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      ),
    );
    const controller = new AbortController();
    const pending = api.streamChat(chatPayload, {
      signal: controller.signal,
      onEvent: vi.fn(),
    });

    controller.abort();

    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
    expect(cancelled).toBe(true);
  });

  it("rechaza eventos start de otra conversación sin exponer sus tokens", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            'event: start\ndata: {"conversation_id":"conversation-ajena","context_revision":1}\n\n' +
              'event: final\ndata: {"answer":"Token ajeno"}\n\n',
            { status: 200, headers: { "Content-Type": "text/event-stream" } },
          ),
        ),
    );
    const onEvent = vi.fn();

    await expect(
      api.streamChat({ ...chatPayload, conversation_id: "conversation-propia" }, { onEvent }),
    ).rejects.toMatchObject({
      detail: { code: "stream_conversation_mismatch" },
    });
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("prioriza el historial por mascota y conserva compatibilidad con servidores anteriores", async () => {
    const finalResponse = finalChatResponse({
      conversation_id: "conversation-history",
      message_id: "message-history",
      answer: "Los leucocitos aumentaron entre los dos estudios.",
      scope: "hemogram_history",
      model: "qwen",
      usage: { prompt_tokens: 20, completion_tokens: 8 },
      duration_ms: 25,
    });
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "pet_id is not permitted" }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(`event: done\ndata: ${JSON.stringify(finalResponse)}\n\n`, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await api.streamChat(
      {
        ...chatPayload,
        context_scope: "hemogram_history",
        pet_id: "pet-1",
        analysis_id: "analysis-latest",
      },
      { onEvent: vi.fn() },
    );

    const firstBody = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    const secondBody = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body));
    expect(firstBody).toMatchObject({
      context_scope: "hemogram_history",
      pet_id: "pet-1",
    });
    expect(firstBody.analysis_id).toBeUndefined();
    expect(secondBody).toMatchObject({
      context_scope: "historical_analysis",
      analysis_id: "analysis-latest",
    });
    expect(secondBody.pet_id).toBeUndefined();
  });

  it("no reenvía el turno cuando el 422 es un veredicto tipado del backend", async () => {
    const envelope = {
      code: "context_budget_exceeded",
      message: "La evidencia imprescindible no cabe de forma segura en el contexto del modelo.",
      detail: "La evidencia imprescindible no cabe de forma segura en el contexto del modelo.",
      category: "validation",
      retryable: false,
      recovery_action: "start_new_conversation",
      request_id: "request-budget",
      client_message_id: chatPayload.client_message_id,
      conversation_id: "conversation-budget",
      retry_after_ms: 0,
      http_status: 422,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: envelope }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.streamChat(
        {
          ...chatPayload,
          context_scope: "selected_hemogram",
          pet_id: "pet-1",
          analysis_id: "analysis-latest",
        },
        { onEvent: vi.fn() },
      ),
    ).rejects.toMatchObject({ status: 422, detail: { code: "context_budget_exceeded" } });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("aborta el stream con un sobre tipado cuando deja de llegar el heartbeat", async () => {
    vi.useFakeTimers();
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            'event: start\ndata: {"conversation_id":"conversation-1","context_revision":1}\n\n',
          ),
        );
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(body, {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        }),
      ),
    );

    const pending = api.streamChat(chatPayload, { onEvent: vi.fn() });
    const assertion = expect(pending).rejects.toMatchObject({
      detail: {
        code: "sse_stalled",
        category: "transport",
        retryable: true,
        recovery_action: "poll_turn",
        conversation_id: "conversation-1",
        http_status: 0,
      },
    });
    await vi.advanceTimersByTimeAsync(40_000);
    await assertion;
    vi.useRealTimers();
  });

  it("limpia localmente cuando el servidor aún no ofrece borrado de conversaciones", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Not found" }), {
          status: 404,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.clearChatConversation("conversation-1")).resolves.toBe(false);
  });

  it("conserva la sesión cuando auth/me confirma que la cookie sigue vigente", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Not authenticated" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ id: "user-1" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.streamChat(chatPayload, { onEvent: vi.fn() })).rejects.toMatchObject({
      status: 401,
      message: "No se pudo autenticar el stream del chat.",
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[1]?.[0]).toBe("/api/v1/auth/me");
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("invalida la sesión solo cuando auth/me también responde 401", async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    const unauthorized = () =>
      new Response(JSON.stringify({ detail: "Token inválido o expirado." }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce(unauthorized()).mockResolvedValueOnce(unauthorized()),
    );

    await expect(api.streamChat(chatPayload, { onEvent: vi.fn() })).rejects.toMatchObject({
      status: 401,
      message: "Tu sesión parece haber expirado.",
    });

    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("limpia todas las conversaciones locales aunque falle el logout remoto", async () => {
    sessionStorage.setItem("hemovet4-chat:v1:owner-1", "legacy");
    sessionStorage.setItem("hemovet4-chat:v2:owner-1", "registry");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

    await expect(api.logout()).rejects.toThrow();

    expect(sessionStorage.getItem("hemovet4-chat:v1:owner-1")).toBeNull();
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).toBeNull();
  });
});

describe("estado del tutorial", () => {
  it("marca el tour como saltado con versión persistida", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "user-1",
          email: "owner@example.com",
          full_name: "Owner",
          created_at: "2026-06-20T10:00:00Z",
          role: "user",
          onboarding_tour_status: "skipped",
          onboarding_tour_version: "hemovet4-main-v1",
          onboarding_tour_dismissed_at: "2026-06-28T22:00:00Z",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const user = await api.updateOnboardingTour({
      status: "skipped",
      version: "hemovet4-main-v1",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/me/onboarding-tour",
      expect.objectContaining({
        method: "PATCH",
        credentials: "include",
        body: JSON.stringify({ status: "skipped", version: "hemovet4-main-v1" }),
      }),
    );
    expect(user.onboarding_tour_status).toBe("skipped");
  });
});
