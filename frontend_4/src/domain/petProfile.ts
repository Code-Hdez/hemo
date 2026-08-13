import type { PetInput, PetProfileExtraction } from "./types";

const currentYear = new Date().getFullYear();

const NAME_KEYS = ["pet_name", "patient_name", "name"];
const BREED_KEYS = ["breed", "raza"];
const SEX_KEYS = ["gender", "sex", "sexo"];
const WEIGHT_KEYS = ["weight_kg", "weight", "peso_kg", "peso"];
const AGE_KEYS = ["age_years", "age", "age_str", "edad"];

export interface SuggestedPetProfile {
  values: Partial<Pick<PetInput, "name" | "breed" | "birth_year" | "sex" | "weight_kg" | "notes">>;
  detectedFields: string[];
}

function cleanText(value: string | null | undefined): string | undefined {
  const normalized = value?.replace(/\s+/g, " ").trim();
  if (!normalized || /^(desconocido|unknown|n\/a|na)$/i.test(normalized)) return undefined;
  return normalized;
}

function firstMetadataValue(
  metadata: Record<string, string | null> | null | undefined,
  keys: string[],
): string | undefined {
  if (!metadata) return undefined;
  for (const key of keys) {
    const direct = cleanText(metadata[key]);
    if (direct) return direct;
    const foundKey = Object.keys(metadata).find(
      (candidate) => candidate.toLowerCase() === key.toLowerCase(),
    );
    const found = foundKey ? cleanText(metadata[foundKey]) : undefined;
    if (found) return found;
  }
  return undefined;
}

function normalizeSex(value: string | undefined): "Hembra" | "Macho" | undefined {
  if (!value) return undefined;
  const normalized = value.toLowerCase();
  if (/^(f|female|hembra|fem|femenino)\b/.test(normalized)) return "Hembra";
  if (/^(m|male|macho|masc|masculino)\b/.test(normalized)) return "Macho";
  return undefined;
}

function parseNumber(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const match = value.replace(",", ".").match(/\d+(?:\.\d+)?/);
  if (!match) return undefined;
  const parsed = Number.parseFloat(match[0]);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function ageYearsFromText(value: string | undefined): number | undefined {
  const direct = parseNumber(value);
  if (!value || direct === undefined) return direct;
  const normalized = value.toLowerCase();
  const years = normalized.match(/(\d+(?:[.,]\d+)?)\s*(?:año|ano|year|yr)/);
  const months = normalized.match(/(\d+(?:[.,]\d+)?)\s*(?:mes|month|mo)/);
  if (!years && !months) return direct;
  const yearValue = years ? Number.parseFloat(years[1].replace(",", ".")) : 0;
  const monthValue = months ? Number.parseFloat(months[1].replace(",", ".")) : 0;
  const total = yearValue + monthValue / 12;
  return Number.isFinite(total) ? total : direct;
}

function birthYearFromAge(ageText: string | undefined): number | undefined {
  const ageYears = ageYearsFromText(ageText);
  if (ageYears === undefined) return undefined;
  const year = currentYear - Math.floor(Math.max(0, ageYears));
  if (year < 1990 || year > currentYear) return undefined;
  return year;
}

export function suggestedPetProfileFromMetadata(
  metadata: Record<string, string | null> | null | undefined,
): SuggestedPetProfile {
  const name = firstMetadataValue(metadata, NAME_KEYS);
  const breed = firstMetadataValue(metadata, BREED_KEYS);
  const sex = normalizeSex(firstMetadataValue(metadata, SEX_KEYS));
  const weight = parseNumber(firstMetadataValue(metadata, WEIGHT_KEYS));
  const birthYear = birthYearFromAge(firstMetadataValue(metadata, AGE_KEYS));
  const detectedFields: string[] = [];
  const values: SuggestedPetProfile["values"] = {};

  if (name) {
    values.name = name;
    detectedFields.push("nombre");
  }
  if (breed) {
    values.breed = breed;
    detectedFields.push("raza");
  }
  if (sex) {
    values.sex = sex;
    detectedFields.push("sexo");
  }
  if (birthYear) {
    values.birth_year = birthYear;
    detectedFields.push("edad");
  }
  if (weight && weight >= 0.5 && weight <= 120) {
    values.weight_kg = Math.round(weight * 10) / 10;
    detectedFields.push("peso");
  }
  if (detectedFields.length > 0) {
    values.notes = `Datos sugeridos desde la ficha del hemograma: ${detectedFields.join(", ")}.`;
  }

  return { values, detectedFields };
}

export function suggestedPetProfileFromExtraction(
  extraction: PetProfileExtraction,
): SuggestedPetProfile {
  const values: SuggestedPetProfile["values"] = {};
  const detectedFields: string[] = [];

  if (extraction.name) {
    values.name = extraction.name;
    detectedFields.push("nombre");
  }
  if (extraction.breed) {
    values.breed = extraction.breed;
    detectedFields.push("raza");
  }
  if (extraction.birth_year) {
    values.birth_year = extraction.birth_year;
    detectedFields.push("año de nacimiento");
  }
  if (extraction.sex) {
    values.sex = extraction.sex;
    detectedFields.push("sexo");
  }
  if (extraction.weight_kg) {
    values.weight_kg = extraction.weight_kg;
    detectedFields.push("peso");
  }
  if (extraction.notes) {
    values.notes = extraction.notes;
    detectedFields.push("notas");
  }

  return { values, detectedFields };
}
