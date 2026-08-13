import { describe, expect, it } from "vitest";
import { chatContextKey, isUnsafeMedicalRequest, visibleChatSources } from "./chat";

describe("isUnsafeMedicalRequest", () => {
  it.each([
    "¿Qué medicamento le doy?",
    "Dime el diagnóstico de Luna",
    "¿Tiene ehrlichia?",
    "¿Cuál es la dosis?",
  ])("bloquea una solicitud clínica fuera de alcance: %s", (message) => {
    expect(isUnsafeMedicalRequest(message)).toBe(true);
  });

  it("permite preguntas educativas sobre parámetros", () => {
    expect(isUnsafeMedicalRequest("¿Qué significa tener los leucocitos altos?")).toBe(false);
  });
});

describe("visibleChatSources", () => {
  it("muestra la bibliografía legible sin campos técnicos", () => {
    const visible = visibleChatSources([
      {
        citation_id: "S1",
        display_title: "Schalm's Veterinary Hematology",
        authors: ["Douglas J. Weiss", "K. Jane Wardrop"],
        edition: "6.ª edición",
        chapter: "Leukocyte disorders",
        section: "Leukocytosis",
        page_start: 123,
        page_end: 125,
        source_type: "book",
        source_id: "schalms_veterinary_hematology_6e_pdf_pages_0101_0150_docling",
        source_path: "/knowledge_base/raw_md/schalm.md",
        score: 0.92,
      },
    ]);

    expect(visible).toEqual([
      {
        key: "citation-0",
        title: "Schalm's Veterinary Hematology, 6.ª edición",
        details: [
          "Autoría: Douglas J. Weiss, K. Jane Wardrop",
          "Capítulo: Leukocyte disorders",
          "Sección: Leukocytosis",
          "Páginas: 123–125",
        ],
      },
    ]);
    expect(JSON.stringify(visible)).not.toContain("_pdf_pages_");
    expect(JSON.stringify(visible)).not.toContain("knowledge_base");
    expect(JSON.stringify(visible)).not.toContain("0.92");
  });

  it("nunca convierte un slug o una ruta en el título visible", () => {
    const [visible] = visibleChatSources([
      {
        source_id: "book-internal",
        title: "cowell_tylers_pdf_pages_0251_docling",
        heading_path: "Leucocitos",
        source_path: "/private/corpus/cowell.pdf",
        score: 0.8,
      },
    ]);

    expect(visible?.title).toBe("Fuente veterinaria consultada");
    expect(visible?.details).toEqual(["Sección: Leucocitos"]);
  });
});

describe("chatContextKey", () => {
  it("aísla el modo, la mascota y el estudio seleccionado", () => {
    expect(chatContextKey("general", "pet-1", "analysis-1")).toBe("general");
    expect(chatContextKey("hemogram_history", "pet-1", "analysis-1")).toBe("history:pet-1");
    expect(chatContextKey("selected_hemogram", "pet-1", "analysis-1")).toBe(
      "analysis:pet-1:analysis-1",
    );
    expect(chatContextKey("selected_hemogram", "pet-1", "analysis-2")).not.toBe(
      chatContextKey("selected_hemogram", "pet-1", "analysis-1"),
    );
  });
});
