import { describe, expect, it } from "vitest";
import { suggestedPetProfileFromExtraction, suggestedPetProfileFromMetadata } from "./petProfile";

describe("sugerencias de mascota desde ficha", () => {
  it("convierte metadatos del hemograma en valores iniciales del formulario", () => {
    const suggestion = suggestedPetProfileFromMetadata({
      pet_name: "Luna",
      breed: "Mestizo",
      gender: "female",
      age_years: "5.4",
      weight_kg: "18,2 kg",
    });

    expect(suggestion.values).toMatchObject({
      name: "Luna",
      breed: "Mestizo",
      sex: "Hembra",
      weight_kg: 18.2,
    });
    expect(suggestion.values.birth_year).toBe(new Date().getFullYear() - 5);
    expect(suggestion.detectedFields).toEqual(["nombre", "raza", "sexo", "edad", "peso"]);
  });

  it("ignora valores vacíos o fuera de rango", () => {
    const suggestion = suggestedPetProfileFromMetadata({
      pet_name: "unknown",
      breed: "",
      age_years: "60",
      weight_kg: "450",
    });

    expect(suggestion.values).toEqual({});
    expect(suggestion.detectedFields).toEqual([]);
  });

  it("convierte la respuesta Gemini de ficha en valores iniciales", () => {
    const suggestion = suggestedPetProfileFromExtraction({
      source: "gemini",
      name: "Bruno",
      breed: "Pug",
      birth_year: 2019,
      sex: "Macho",
      weight_kg: 8.5,
      notes: "Ficha de control.",
      detected_fields: ["nombre", "raza"],
      warnings: [],
    });

    expect(suggestion.values).toMatchObject({
      name: "Bruno",
      breed: "Pug",
      birth_year: 2019,
      sex: "Macho",
      weight_kg: 8.5,
      notes: "Ficha de control.",
    });
  });
});
