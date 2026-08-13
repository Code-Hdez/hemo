import { describe, expect, it } from "vitest";
import type { AnalysisResult, Pet, PetInput } from "../domain/types";
import { buildMockPublicPoints, sanitizeMockResidence } from "./residence";

function pet(id: string, lat = 19.4601, lng = -70.6912): Pet {
  return {
    id,
    owner_id: "user-owner",
    name: `Mascota ${id}`,
    breed: "Mestiza",
    birth_year: 2020,
    sex: "Hembra",
    weight_kg: 10,
    notes: "",
    residence_zone_code: "do-grid-p973-m3535",
    residence_label: "Santiago - zona A1B2",
    residence_lat: lat,
    residence_lng: lng,
    residence_precision: "grid_2km",
    residence_consent: true,
    created_at: new Date().toISOString(),
    image: "data:image/svg+xml;base64,PHN2Zy8+",
  };
}

function analysis(id: string, petId: string): AnalysisResult {
  return {
    id,
    pet_id: petId,
    created_at: new Date().toISOString(),
    findings: [
      {
        label: "Patrón inflamatorio",
        detail: "Detalle mock",
        severity: "warn",
        glossary_slug: "patron-inflamatorio",
      },
    ],
  } as AnalysisResult;
}

const input: PetInput = {
  name: "Milo",
  breed: "Mestiza",
  birth_year: 2021,
  sex: "Macho",
  weight_kg: 12,
  notes: "",
  residence_lat: 19.4601,
  residence_lng: -70.6912,
  residence_source: "pin",
  residence_consent: true,
};

describe("residencia mock para vigilancia", () => {
  it("cuantiza un pin consentido antes de guardarlo", () => {
    const residence = sanitizeMockResidence(input);

    expect(residence.residence_zone_code).toMatch(/^do-grid-/);
    expect(residence.residence_precision).toBe("grid_2km");
    expect(residence.residence_lat).not.toBe(input.residence_lat);
    expect(residence.residence_lng).not.toBe(input.residence_lng);
  });

  it("no conserva ubicación cuando no hay consentimiento", () => {
    const residence = sanitizeMockResidence({ ...input, residence_consent: false });

    expect(residence).toMatchObject({
      residence_consent: false,
      residence_lat: undefined,
      residence_lng: undefined,
    });
  });

  it("publica una zona solo con tres reportes de tres mascotas y usa un desplazamiento estable", () => {
    const pets = [pet("pet-1"), pet("pet-2", 19.462, -70.69), pet("pet-3", 19.464, -70.688)];
    const analyses = [
      analysis("analysis-1", "pet-1"),
      analysis("analysis-2", "pet-2"),
      analysis("analysis-3", "pet-3"),
    ];

    expect(buildMockPublicPoints(pets.slice(0, 2), analyses.slice(0, 2), 90)).toEqual([]);

    const points = buildMockPublicPoints(pets, analyses, 90);
    expect(points).toHaveLength(1);
    expect(points[0]).toMatchObject({ report_count: 3, pet_count: 3, intensity_level: "low" });
    expect(points[0]?.lat).not.toBe(pets[0]?.residence_lat);
    expect(points).toEqual(buildMockPublicPoints(pets, analyses, 90));
  });
});
