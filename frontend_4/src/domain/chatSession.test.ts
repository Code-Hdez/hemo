import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  browserChatSessionId,
  clearAllChatSessionManifests,
  clearChatSessionManifest,
  loadChatSessionManifest,
  loadChatSessionRegistry,
  saveChatSessionManifest,
} from "./chatSession";

const base = {
  version: 2 as const,
  userId: "owner-1",
  contextRevision: 1,
  updatedAt: "2026-07-18T12:00:00.000Z",
};

describe("chat session registry v2", () => {
  beforeEach(() => {
    clearAllChatSessionManifests();
    sessionStorage.clear();
  });

  it("mantiene un identificador efímero solo durante la sesión del navegador", () => {
    const first = browserChatSessionId();
    const second = browserChatSessionId();

    expect(second).toBe(first);
    expect(first).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);

    clearAllChatSessionManifests();
    expect(browserChatSessionId()).not.toBe(first);
  });

  it("conserva un único identificador de página cuando sessionStorage está bloqueado", () => {
    clearAllChatSessionManifests();
    const getItem = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });

    const first = browserChatSessionId();
    const second = browserChatSessionId();

    expect(second).toBe(first);
    expect(first).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
    getItem.mockRestore();
  });

  it("conserva una conversación aislada por contextKey", () => {
    saveChatSessionManifest({
      ...base,
      conversationId: "conversation-general",
      scope: "general",
      contextKey: "general",
    });
    saveChatSessionManifest({
      ...base,
      conversationId: "conversation-history",
      scope: "hemogram_history",
      contextKey: "history:pet-1",
      petId: "pet-1",
      updatedAt: "2026-07-18T12:01:00.000Z",
    });

    expect(loadChatSessionManifest("owner-1", "general")?.conversationId).toBe(
      "conversation-general",
    );
    expect(loadChatSessionManifest("owner-1", "history:pet-1")?.conversationId).toBe(
      "conversation-history",
    );
    expect(loadChatSessionRegistry("owner-1").activeContextKey).toBe("history:pet-1");
  });

  it("migra el manifiesto v1 sin guardar mensajes clínicos", () => {
    sessionStorage.setItem(
      "hemovet4-chat:v1:owner-1",
      JSON.stringify({
        version: 1,
        userId: "owner-1",
        conversationId: "conversation-legacy",
        contextRevision: 3,
        scope: "selected_hemogram",
        contextKey: "analysis:pet-1:analysis-1",
        petId: "pet-1",
        analysisId: "analysis-1",
        messages: [{ content: "valor clínico que no debe persistirse" }],
        updatedAt: "2026-07-18T12:00:00.000Z",
      }),
    );

    expect(loadChatSessionManifest("owner-1", "analysis:pet-1:analysis-1")?.conversationId).toBe(
      "conversation-legacy",
    );
    expect(sessionStorage.getItem("hemovet4-chat:v1:owner-1")).toBeNull();
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).not.toContain("content");
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).not.toContain("valor clínico");
  });

  it("elimina un contexto sin afectar los demás y limpia todo al cerrar sesión", () => {
    saveChatSessionManifest({
      ...base,
      conversationId: "conversation-general",
      scope: "general",
      contextKey: "general",
    });
    saveChatSessionManifest({
      ...base,
      conversationId: "conversation-analysis",
      scope: "selected_hemogram",
      contextKey: "analysis:pet-1:analysis-1",
      petId: "pet-1",
      analysisId: "analysis-1",
    });

    clearChatSessionManifest("owner-1", "general");
    expect(loadChatSessionManifest("owner-1", "general")).toBeUndefined();
    expect(loadChatSessionManifest("owner-1", "analysis:pet-1:analysis-1")?.conversationId).toBe(
      "conversation-analysis",
    );

    clearAllChatSessionManifests();
    expect(loadChatSessionRegistry("owner-1").contexts).toEqual({});
  });

  it("rechaza registros de otro usuario o entradas corruptas", () => {
    sessionStorage.setItem(
      "hemovet4-chat:v2:owner-1",
      JSON.stringify({ version: 2, userId: "owner-2", contexts: {} }),
    );
    expect(loadChatSessionRegistry("owner-1").contexts).toEqual({});
    expect(sessionStorage.getItem("hemovet4-chat:v2:owner-1")).toBeNull();
  });
});
