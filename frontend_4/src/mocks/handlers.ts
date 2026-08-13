import { delay, HttpResponse, http } from "msw";
import defaultPetImage from "../assets/dog-head-profile.svg";
import { CBC_REVIEW_FIELDS } from "../domain/analysis";
import { isUnsafeMedicalRequest } from "../domain/chat";
import type { AnalysisResult, Pet, PetInput } from "../domain/types";
import {
  analyses,
  epidemiologyPoints,
  modelQuality,
  pets,
  setAnalyses,
  setPets,
  users,
} from "./data";
import { buildMockPublicPoints, sanitizeMockResidence } from "./residence";

let activeMockUser = null as (typeof users)[number] | null;
const chatHealthChecksByToken = new Map<string, number>();
const tourStateByToken = new Map<
  string,
  Pick<
    (typeof users)[number],
    "onboarding_tour_status" | "onboarding_tour_version" | "onboarding_tour_dismissed_at"
  >
>([
  [
    "owner-completed-token",
    {
      onboarding_tour_status: "completed",
      onboarding_tour_version: "hemovet4-main-v1",
      onboarding_tour_dismissed_at: "2026-06-28T12:00:00Z",
    },
  ],
]);

function authUser(request: Request) {
  const token = request.headers.get("Authorization")?.replace("Bearer ", "");
  const baseUser =
    token === "owner-demo-token" ||
    token?.startsWith("owner-chat-recovery-token") ||
    token?.startsWith("owner-pending-token") ||
    token?.startsWith("owner-completed-token")
      ? users[0]
      : token === "admin-demo-token"
        ? users[1]
        : token === "empty-owner-demo-token" || token?.startsWith("empty-owner-pending-token")
          ? users[2]
          : null;
  if (!baseUser) return null;
  const defaultCompletedState =
    token?.startsWith("owner-completed-token") || token === "admin-demo-token"
      ? {
          onboarding_tour_status: "completed" as const,
          onboarding_tour_version: "hemovet4-main-v1",
          onboarding_tour_dismissed_at: "2026-06-28T12:00:00Z",
        }
      : undefined;
  const tourState = token ? (tourStateByToken.get(token) ?? defaultCompletedState) : undefined;
  return tourState ? { ...baseUser, ...tourState } : baseUser;
}

function authToken(request: Request): string | null {
  return request.headers.get("Authorization")?.replace("Bearer ", "") ?? null;
}

function requireUser(request: Request) {
  const user = authUser(request);
  if (!user)
    return HttpResponse.json(
      { detail: "La sesión expiró. Inicia sesión nuevamente." },
      { status: 401 },
    );
  return user;
}

export const handlers = [
  http.post("/api/v1/auth/login", async ({ request }) => {
    await delay(260);
    const body = new URLSearchParams(await request.text());
    const email = body.get("username")?.toLowerCase();
    const password = body.get("password");
    if (password !== "Demo1234" || !users.some((user) => user.email === email)) {
      return HttpResponse.json({ detail: "Email o contraseña incorrectos." }, { status: 401 });
    }
    activeMockUser = users.find((user) => user.email === email) ?? null;
    const token =
      activeMockUser?.id === "user-admin"
        ? "admin-demo-token"
        : activeMockUser?.id === "user-empty"
          ? "empty-owner-demo-token"
          : "owner-demo-token";
    return HttpResponse.json({
      access_token: token,
      token_type: "bearer",
    });
  }),

  http.post("/api/v1/auth/logout", () => {
    activeMockUser = null;
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/v1/auth/register", async ({ request }) => {
    await delay(300);
    const payload = (await request.json()) as {
      full_name: string;
      email: string;
      password: string;
    };
    if (users.some((user) => user.email === payload.email.toLowerCase())) {
      return HttpResponse.json({ detail: "Ya existe una cuenta con ese email." }, { status: 409 });
    }
    return HttpResponse.json(
      {
        id: crypto.randomUUID(),
        email: payload.email,
        full_name: payload.full_name,
        role: "user",
        created_at: new Date().toISOString(),
        onboarding_tour_status: "pending",
        onboarding_tour_version: null,
        onboarding_tour_dismissed_at: null,
      },
      { status: 201 },
    );
  }),

  http.get("/api/v1/auth/me", ({ request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    return HttpResponse.json(user);
  }),

  http.patch("/api/v1/auth/me/onboarding-tour", async ({ request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const token = authToken(request);
    const payload = (await request.json()) as {
      status: "completed" | "skipped";
      version: string;
    };
    const tourState = {
      onboarding_tour_status: payload.status,
      onboarding_tour_version: payload.version,
      onboarding_tour_dismissed_at: new Date().toISOString(),
    } as const;
    if (token) tourStateByToken.set(token, tourState);
    return HttpResponse.json({ ...user, ...tourState });
  }),

  http.get("/api/v1/breeds", () =>
    HttpResponse.json([
      "Mestiza",
      "Labrador retriever",
      "Golden retriever",
      "Pastor alemán",
      "Beagle",
      "Poodle",
      "Chihuahua",
      "Bulldog francés",
    ]),
  ),

  http.get("/api/v1/residence/zones", () =>
    HttpResponse.json([
      {
        code: "do-stgo-santiago",
        label: "Santiago",
        province: "Santiago",
        municipality: "Santiago de los Caballeros",
        lat: 19.4517,
        lng: -70.697,
        precision: "municipality",
      },
      {
        code: "do-sd-dn",
        label: "Distrito Nacional",
        province: "Distrito Nacional",
        municipality: "Santo Domingo de Guzmán",
        lat: 18.4861,
        lng: -69.9312,
        precision: "municipality",
      },
    ]),
  ),

  http.post("/api/v1/residence/resolve", async ({ request }) => {
    const payload = (await request.json()) as { query: string };
    return HttpResponse.json(
      payload.query.trim().length >= 3
        ? [
            {
              id: "candidate-santiago",
              label: "Santiago de los Caballeros",
              lat: 19.4517,
              lng: -70.697,
              precision: "municipality",
              source: "nominatim",
            },
          ]
        : [],
    );
  }),

  http.post("/api/v1/residence/nearby-veterinary-care", async ({ request }) => {
    await delay(220);
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const payload = (await request.json()) as {
      pet_id?: string;
      radius_meters?: number;
    };
    const pet = pets.find((item) => item.id === payload.pet_id && item.owner_id === user.id);
    if (!pet) {
      return HttpResponse.json({ detail: "Mascota no encontrada." }, { status: 404 });
    }
    if (
      !pet.residence_consent ||
      typeof pet.residence_lat !== "number" ||
      typeof pet.residence_lng !== "number"
    ) {
      return HttpResponse.json(
        {
          detail: "Activa la ubicación aproximada de tu mascota para buscar atención cercana.",
        },
        { status: 422 },
      );
    }

    const radiusMeters = payload.radius_meters ?? 10_000;
    const places = [
      {
        name: "Centro Veterinario Comunitario",
        lat: pet.residence_lat + 0.01,
        lng: pet.residence_lng - 0.006,
        distance_meters: 1_420,
        address: "Av. Principal, zona urbana",
        osm_url: "https://www.openstreetmap.org/node/1001",
      },
      {
        name: "Clínica Veterinaria Las Palmas",
        lat: pet.residence_lat - 0.025,
        lng: pet.residence_lng + 0.018,
        distance_meters: 3_480,
        address: null,
        osm_url: "https://www.openstreetmap.org/node/1002",
      },
      {
        name: "Hospital Veterinario Regional",
        lat: pet.residence_lat + 0.08,
        lng: pet.residence_lng + 0.04,
        distance_meters: 11_600,
        address: "Carretera regional",
        osm_url: "https://www.openstreetmap.org/way/1003",
      },
    ].filter((place) => place.distance_meters <= radiusMeters);

    return HttpResponse.json({
      items: places,
      source: "openstreetmap",
      search_url: `https://www.openstreetmap.org/search?query=${encodeURIComponent(
        `veterinaria ${pet.residence_label ?? "República Dominicana"}`,
      )}`,
      location_precision: pet.residence_precision ?? "approximate",
      message: places.length
        ? "Estas son ubicaciones públicas aproximadas; llama antes de trasladarte."
        : "No se pudieron confirmar centros ahora. Usa la búsqueda de OpenStreetMap o contacta un servicio local.",
    });
  }),

  http.get("/api/v1/pets", async ({ request }) => {
    await delay(160);
    const user = requireUser(request);
    if (user instanceof Response) return user;
    return HttpResponse.json(pets.filter((pet) => pet.owner_id === user.id));
  }),

  http.get("/api/v1/pets/:petId", ({ params, request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const pet = pets.find((item) => item.id === params.petId);
    return pet
      ? HttpResponse.json(pet)
      : HttpResponse.json({ detail: "Mascota no encontrada." }, { status: 404 });
  }),

  http.post("/api/v1/pets", async ({ request }) => {
    await delay(350);
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const payload = (await request.json()) as PetInput;
    const residence = sanitizeMockResidence(payload);
    if (!payload.residence_consent) {
      return HttpResponse.json(
        { detail: "Confirma el consentimiento para registrar la ubicación agregada." },
        { status: 422 },
      );
    }
    if (!residence.residence_consent) {
      return HttpResponse.json({ detail: "La ubicación es obligatoria." }, { status: 422 });
    }
    const { residence_source: _residenceSource, ...petInput } = payload;
    const pet: Pet = {
      ...petInput,
      ...residence,
      id: `pet-${crypto.randomUUID().slice(0, 8)}`,
      owner_id: user.id,
      created_at: new Date().toISOString(),
    };
    setPets([...pets, pet]);
    return HttpResponse.json(pet, { status: 201 });
  }),

  http.put("/api/v1/pets/:petId", async ({ params, request }) => {
    await delay(240);
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const payload = (await request.json()) as PetInput;
    const current = pets.find((pet) => pet.id === params.petId);
    if (!current) return HttpResponse.json({ detail: "Mascota no encontrada." }, { status: 404 });
    const residence = sanitizeMockResidence(payload);
    if (!payload.residence_consent) {
      return HttpResponse.json(
        { detail: "Confirma el consentimiento para registrar la ubicación agregada." },
        { status: 422 },
      );
    }
    if (!residence.residence_consent) {
      return HttpResponse.json({ detail: "La ubicación es obligatoria." }, { status: 422 });
    }
    const { residence_source: _residenceSource, ...petInput } = payload;
    const updated: Pet = {
      ...current,
      ...petInput,
      ...residence,
    };
    setPets(pets.map((pet) => (pet.id === params.petId ? updated : pet)));
    return HttpResponse.json(updated);
  }),

  http.post("/api/v1/pets/:petId/photo", async ({ params, request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const photo = (await request.formData()).get("file");
    if (!(photo instanceof File)) {
      return HttpResponse.json({ detail: "Selecciona una imagen válida." }, { status: 400 });
    }
    const current = pets.find((pet) => pet.id === params.petId);
    if (!current) return HttpResponse.json({ detail: "Mascota no encontrada." }, { status: 404 });
    const updated: Pet = { ...current, image: defaultPetImage, photo_url: defaultPetImage };
    setPets(pets.map((pet) => (pet.id === params.petId ? updated : pet)));
    return HttpResponse.json(updated);
  }),

  http.delete("/api/v1/pets/:petId/photo", ({ params, request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const current = pets.find((pet) => pet.id === params.petId);
    if (!current) return HttpResponse.json({ detail: "Mascota no encontrada." }, { status: 404 });
    const updated: Pet = { ...current, image: undefined, photo_url: null };
    setPets(pets.map((pet) => (pet.id === params.petId ? updated : pet)));
    return HttpResponse.json(updated);
  }),

  http.delete("/api/v1/pets/:petId", ({ params, request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    setPets(pets.filter((pet) => pet.id !== params.petId));
    return new HttpResponse(null, { status: 204 });
  }),

  http.post("/api/v1/extract", async ({ request }) => {
    await delay(950);
    const form = await request.formData();
    const file = form.get("file");
    if (!(file instanceof File)) {
      return HttpResponse.json(
        { detail: "Selecciona un archivo de hemograma válido." },
        { status: 422 },
      );
    }
    const cbc = {
      WBC: 18.6,
      Neutrophils: 14.2,
      RBC: 6.18,
      HGB: 14.6,
      HCT: 42.8,
      Platelets: 112,
    };
    return HttpResponse.json({
      cbc,
      fields: CBC_REVIEW_FIELDS.map((field) => ({
        ...field,
        value: cbc[field.key as keyof typeof cbc]?.toString() ?? "",
        detected: field.key in cbc,
      })),
      metadata: {
        patient_name: "Luna",
        species: "Canina",
        result_date: "2026-06-10",
        instrument: "IDEXX ProCyte One",
      },
      comments: "El informe original sugiere revisar el conteo plaquetario.",
      extraction_provider: "gemini",
      extraction_mode: "auto",
      fallback_used: false,
      warnings: ["El valor de plaquetas presenta una lectura dudosa y debe revisarse."],
    });
  }),

  http.post("/api/v1/analyze/confirmed", async ({ request }) => {
    await delay(1100);
    const user = authUser(request);
    const payload = (await request.json()) as {
      cbc: Record<string, number>;
      filename: string;
      file_size: number;
      pet_id?: string;
    };
    const pet =
      user && payload.pet_id
        ? pets.find((item) => item.id === payload.pet_id && item.owner_id === user.id)
        : null;
    if (payload.pet_id && !pet) {
      return HttpResponse.json({ detail: "Selecciona una mascota registrada." }, { status: 422 });
    }
    const base = analyses[0];
    const labValueAliases: Record<string, string> = {
      NEU: "Neutrophils",
      PLT: "Platelets",
    };
    const created: AnalysisResult = {
      ...base,
      id: `analysis-${crypto.randomUUID().slice(0, 8)}`,
      prediction_id: crypto.randomUUID(),
      filename: payload.filename,
      file_size: payload.file_size,
      created_at: new Date().toISOString(),
      pet_id: pet?.id ?? null,
      pet_name: pet?.name ?? null,
      residence_zone_code: pet?.residence_zone_code ?? null,
      residence_label: pet?.residence_label ?? null,
      persisted: Boolean(user && pet),
      lab_values: base.lab_values.map((value) => ({
        ...value,
        value: String(
          payload.cbc[value.name] ?? payload.cbc[labValueAliases[value.name]] ?? value.value,
        ),
      })),
    };
    if (created.persisted) setAnalyses([created, ...analyses]);
    return HttpResponse.json(created);
  }),

  http.get("/api/v1/history", async ({ request }) => {
    await delay(180);
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const petId = new URL(request.url).searchParams.get("pet_id");
    const userPetIds = new Set(pets.filter((pet) => pet.owner_id === user.id).map((pet) => pet.id));
    return HttpResponse.json(
      analyses
        .filter((analysis) => analysis.pet_id && userPetIds.has(analysis.pet_id))
        .filter((analysis) => !petId || analysis.pet_id === petId)
        .sort((a, b) => b.created_at.localeCompare(a.created_at)),
    );
  }),

  http.get("/api/v1/analysis/:analysisId", ({ params, request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    const analysis = analyses.find((item) => item.id === params.analysisId);
    return analysis
      ? HttpResponse.json(analysis)
      : HttpResponse.json({ detail: "Análisis no encontrado." }, { status: 404 });
  }),

  http.get("/api/v1/epidemiology/points", async ({ request }) => {
    await delay(260);
    const requestedPeriod = Number(new URL(request.url).searchParams.get("period_days") ?? "90");
    const periodDays = Number.isFinite(requestedPeriod) ? requestedPeriod : 90;
    return HttpResponse.json([
      ...epidemiologyPoints,
      ...buildMockPublicPoints(pets, analyses, periodDays),
    ]);
  }),

  http.get("/api/v1/surveillance/report", () =>
    HttpResponse.json({
      generated_at: new Date().toISOString(),
      period_days: 90,
      cohort_size: analyses.length,
      status: "pass",
      status_counts: { pass: 1, warn: 0, fail: 0 },
      temporal_signals: [],
      geographic_hotspots: [],
      gate_status: { feature_parity: "pass" },
    }),
  ),

  http.get("/api/v1/analytics/temporal", () =>
    HttpResponse.json({
      timeline: [
        {
          period: "2026-W20",
          n_analyses: 2,
          mean_confidence: 0.88,
          qc_flag_pct: 0,
          top_finding: "Plaquetas bajas",
        },
        {
          period: "2026-W21",
          n_analyses: 1,
          mean_confidence: 0.91,
          qc_flag_pct: 0,
          top_finding: "Leucograma de estrés",
        },
      ],
      granularity: "week",
      period_days: 90,
    }),
  ),

  http.post("/api/v1/chat", async ({ request }) => {
    await delay(320);
    const payload = (await request.json()) as {
      message: string;
      context_scope:
        | "general"
        | "selected_hemogram"
        | "hemogram_history"
        | "uploaded_analysis"
        | "historical_analysis";
      conversation_id?: string;
    };
    const unsafe = isUnsafeMedicalRequest(payload.message);
    const contextual = payload.context_scope !== "general";
    return HttpResponse.json({
      conversation_id: payload.conversation_id ?? "conversation-demo",
      message_id: crypto.randomUUID(),
      answer: unsafe
        ? "No puedo indicar diagnósticos, medicamentos, tratamientos ni dosis. Consulta con un veterinario que conozca el caso."
        : contextual
          ? "En el hemograma seleccionado, los leucocitos están por encima del intervalo informado. Esto es un hallazgo descriptivo y no permite confirmar una causa."
          : "Puedo explicar valores y patrones del hemograma canino en lenguaje sencillo, sin emitir diagnósticos.",
      scope: payload.context_scope,
      sources: unsafe
        ? []
        : [
            {
              citation_id: "S1",
              display_title: "Schalm's Veterinary Hematology",
              authors: ["Douglas J. Weiss", "K. Jane Wardrop"],
              edition: "6.ª edición",
              chapter: "Trastornos leucocitarios",
              section: "Leucocitosis",
              page_start: 123,
              page_end: 125,
              source_type: "book",
            },
          ],
      case_facts: contextual ? [{ parameter: "WBC", value: "18.6" }] : [],
      warnings: ["La respuesta es educativa y no sustituye una evaluación veterinaria"],
      safety_action: unsafe ? "refuse" : "allow",
      model: unsafe ? null : "mock-rag",
      usage: { prompt_tokens: 42, completion_tokens: 24 },
      duration_ms: 320,
      finish_reason: "stop",
      llm_invoked: !unsafe,
      response_origin: unsafe ? "legacy" : "llm",
      attempt: 1,
      generation_attempts: unsafe ? 0 : 1,
      stream_mode: "buffered_validated",
      validation_status: "passed",
    });
  }),

  http.get("/api/v1/chat/health", ({ request }) => {
    const token = authToken(request) ?? "anonymous";
    const checks = (chatHealthChecksByToken.get(token) ?? 0) + 1;
    chatHealthChecksByToken.set(token, checks);
    const providerReady = !token.startsWith("owner-chat-recovery-token") || checks >= 3;
    return HttpResponse.json({
      contract_version: "hemovet.availability/v1",
      probe: "chat_availability",
      status: providerReady ? "ok" : "fail",
      chat_ready: providerReady,
      degraded: false,
      module_ready: true,
      provider_ready: providerReady,
      llm_ready: providerReady,
      rag_required: true,
      rag_ready: true,
      chroma_ready: true,
      collection_ready: true,
      codes: providerReady ? [] : ["LLM_PROVIDER_UNAVAILABLE"],
      provider: {
        contract_version: "hemovet.availability/v1",
        probe: "provider_availability",
        status: providerReady ? "ready" : "unavailable",
        provider: "mock",
        model: "qwen3:4b-instruct-2507-q4_K_M",
        ready: providerReady,
        code: providerReady ? null : "LLM_PROVIDER_UNAVAILABLE",
        retryable: !providerReady,
        identity_verified: providerReady,
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
    });
  }),

  http.post("/api/v1/chat/stream", async ({ request }) => {
    await delay(120);
    const payload = (await request.json()) as {
      message: string;
      context_scope:
        | "general"
        | "selected_hemogram"
        | "hemogram_history"
        | "uploaded_analysis"
        | "historical_analysis";
      conversation_id?: string;
    };
    if (payload.message.startsWith("__TEST_STREAM_401__")) {
      return HttpResponse.json({ detail: "Sesión no válida para el stream." }, { status: 401 });
    }
    const unsafe = isUnsafeMedicalRequest(payload.message);
    const contextual = payload.context_scope !== "general";
    const result = {
      conversation_id: payload.conversation_id ?? "conversation-demo",
      message_id: crypto.randomUUID(),
      answer: unsafe
        ? "No puedo indicar diagnósticos, medicamentos, tratamientos ni dosis. Consulta con un veterinario que conozca el caso."
        : contextual
          ? "En el hemograma seleccionado, los leucocitos están por encima del intervalo informado. Esto es un hallazgo descriptivo y no permite confirmar una causa."
          : "Puedo explicar valores y patrones del hemograma canino en lenguaje sencillo, sin emitir diagnósticos.",
      scope: payload.context_scope,
      sources: unsafe
        ? []
        : [
            {
              citation_id: "S1",
              display_title: "Schalm's Veterinary Hematology",
              authors: ["Douglas J. Weiss", "K. Jane Wardrop"],
              edition: "6.ª edición",
              chapter: "Trastornos leucocitarios",
              section: "Leucocitosis",
              page_start: 123,
              page_end: 125,
              source_type: "book",
            },
          ],
      case_facts: contextual ? [{ parameter: "WBC", value: "18.6" }] : [],
      warnings: ["La respuesta es educativa y no sustituye una evaluación veterinaria"],
      safety_action: unsafe ? "refuse" : "allow",
      model: unsafe ? null : "mock-rag",
      usage: { prompt_tokens: 42, completion_tokens: 24 },
      duration_ms: 320,
      finish_reason: "stop",
      llm_invoked: !unsafe,
      response_origin: unsafe ? "legacy" : "llm",
      attempt: 1,
      generation_attempts: unsafe ? 0 : 1,
      stream_mode: "buffered_validated",
      validation_status: "passed",
    };
    if (payload.message.startsWith("__TEST_PROGRESSIVE_STREAM__")) {
      result.answer = "Los leucocitos se muestran de forma progresiva.";
      const encoder = new TextEncoder();
      let finalChunkTimer: ReturnType<typeof setTimeout> | undefined;
      const body = new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            encoder.encode(
              `event: start\ndata: ${JSON.stringify({
                conversation_id: result.conversation_id,
                context_revision: 1,
                attempt: 1,
              })}\n\n` +
                `event: context_ready\ndata: ${JSON.stringify({
                  conversation_id: result.conversation_id,
                  context_revision: 1,
                  mode: payload.context_scope,
                })}\n\n` +
                'event: generation_started\ndata: {"stream_mode":"live_validated","generation_attempt":1}\n\n',
            ),
          );
          finalChunkTimer = setTimeout(() => {
            controller.enqueue(
              encoder.encode(
                `event: final\ndata: ${JSON.stringify(result)}\n\n` +
                  `event: done\ndata: ${JSON.stringify(result)}\n\n`,
              ),
            );
            controller.close();
          }, 500);
        },
        cancel() {
          if (finalChunkTimer) clearTimeout(finalChunkTimer);
        },
      });
      return new HttpResponse(body, {
        headers: {
          "Cache-Control": "no-cache, no-transform",
          "Content-Type": "text/event-stream",
        },
      });
    }
    const body = [
      `event: start\ndata: ${JSON.stringify({ conversation_id: result.conversation_id, context_revision: 1, attempt: 1 })}\n\n`,
      `event: context_ready\ndata: ${JSON.stringify({ conversation_id: result.conversation_id, context_revision: 1, mode: payload.context_scope })}\n\n`,
      'event: generation_started\ndata: {"stream_mode":"buffered_validated","generation_attempt":1}\n\n',
      'event: status\ndata: {"stage":"validating"}\n\n',
      `event: final\ndata: ${JSON.stringify(result)}\n\n`,
      `event: done\ndata: ${JSON.stringify(result)}\n\n`,
    ].join("");
    return new HttpResponse(body, { headers: { "Content-Type": "text/event-stream" } });
  }),

  // The mock backend keeps no conversation registry, so there is never an
  // active one to reuse and the page always creates a fresh conversation.
  http.get("/api/v1/chat/conversations", () => HttpResponse.json({ items: [] })),

  http.post("/api/v1/chat/conversations", async ({ request }) => {
    const payload = (await request.json()) as {
      context_scope: string;
      analysis_id?: string;
      pet_id?: string;
    };
    return HttpResponse.json(
      {
        id: crypto.randomUUID(),
        mode: payload.context_scope,
        pet_id: payload.pet_id ?? null,
        analysis_id: payload.analysis_id ?? null,
        context_revision: 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        expires_at: null,
      },
      { status: 201 },
    );
  }),

  http.delete(
    "/api/v1/chat/conversations/:conversationId",
    () => new HttpResponse(null, { status: 204 }),
  ),

  http.get("/api/v1/model/quality", ({ request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    if (user.role !== "admin") {
      return HttpResponse.json(
        { detail: "No tienes permiso para ver el panel técnico." },
        { status: 403 },
      );
    }
    return HttpResponse.json(modelQuality);
  }),

  http.get("/api/v1/analytics/label-activation", ({ request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    return HttpResponse.json({ labels: [] });
  }),

  http.get("/api/v1/analytics/breed-distribution", ({ request }) => {
    const user = requireUser(request);
    if (user instanceof Response) return user;
    return HttpResponse.json({ breeds: [], period_days: 30, total: 0 });
  }),
];
