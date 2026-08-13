import { describe, expect, it } from "vitest";
import { cleanVisibleAssistantText, SseParser } from "./chatStream";

describe("SseParser", () => {
  it("conserva frames parciales y emite eventos completos en orden", () => {
    const parser = new SseParser();

    expect(parser.push('event: status\ndata: {"stage":"valid')).toEqual([]);
    expect(parser.push('ated"}\n\nevent: delta\ndata: {"text":"Respuesta segura"}\n\n')).toEqual([
      { event: "status", data: { stage: "validated" } },
      { event: "delta", data: { text: "Respuesta segura" } },
    ]);
  });

  it("ignora keepalive y rechaza JSON inválido", () => {
    const parser = new SseParser();

    expect(parser.push(": keepalive\n\n")).toEqual([]);
    expect(() => parser.push("event: delta\ndata: no-json\n\n")).toThrow("Evento SSE inválido");
  });

  it("tolera CRLF dividido entre fragmentos y vacía el último evento al llegar EOF", () => {
    const parser = new SseParser();

    expect(parser.push('event: context\r\ndata: {"conversation_id":"chat-1"}\r')).toEqual([]);
    expect(parser.push('\n\r\nevent: delta\r\ndata: {"text":"Hola"}')).toEqual([
      { event: "context", data: { conversation_id: "chat-1" } },
    ]);
    expect(parser.finish()).toEqual([{ event: "delta", data: { text: "Hola" } }]);
  });

  it("reconstruye JSON distribuido en varias líneas data", () => {
    const parser = new SseParser();

    expect(parser.push('event: status\ndata: {"stage":\ndata: "generating"}\n\n')).toEqual([
      { event: "status", data: { stage: "generating" } },
    ]);
  });
});

describe("cleanVisibleAssistantText", () => {
  it("elimina citas inline sin alterar espacios de streaming cuando se solicita", () => {
    expect(cleanVisibleAssistantText("Respuesta [S1, S2].")).toBe("Respuesta.");
    expect(cleanVisibleAssistantText("Respuesta ", { trim: false })).toBe("Respuesta ");
  });
});
