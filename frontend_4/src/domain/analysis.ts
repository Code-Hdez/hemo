import cbcFieldDefinitions from "../../../shared/cbc_fields.json";
import type { ExtractedCbcField, ExtractionResponse } from "./types";

export const CORE_CBC_KEYS = ["WBC", "RBC", "HGB", "HCT", "Platelets"] as const;

export function hasEnoughCoreValues(values: Record<string, number>, minimum = 3): boolean {
  return CORE_CBC_KEYS.filter((key) => Number.isFinite(values[key])).length >= minimum;
}

export interface CbcReviewField {
  key: string;
  label: string;
  unit: string;
  required: boolean;
  group: string;
  order: number;
}

interface SharedCbcField extends CbcReviewField {
  aliases: string[];
}

const SHARED_CBC_FIELDS = cbcFieldDefinitions as SharedCbcField[];

export const CBC_REVIEW_FIELDS: CbcReviewField[] = SHARED_CBC_FIELDS.map(
  ({ aliases: _aliases, ...field }) => field,
);

const FIELD_ALIASES: Record<string, string> = Object.fromEntries(
  SHARED_CBC_FIELDS.flatMap((field) => [
    [field.key.toLowerCase(), field.key],
    ...field.aliases.map((alias) => [alias.toLowerCase(), field.key] as const),
  ]),
);

export function splitReviewFields(
  fields: CbcReviewField[] = CBC_REVIEW_FIELDS,
): [CbcReviewField[], CbcReviewField[]] {
  const sorted = [...fields].sort((a, b) => a.order - b.order);
  return [sorted.slice(0, 12), sorted.slice(12, 24)];
}

function canonicalKey(key: string): string {
  return FIELD_ALIASES[key.trim().toLowerCase()] ?? key;
}

function valueToString(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

export function buildInitialReviewValues(
  extraction: Pick<ExtractionResponse, "cbc"> & { fields?: ExtractedCbcField[] },
): Record<string, string> {
  const values = Object.fromEntries(CBC_REVIEW_FIELDS.map((field) => [field.key, ""]));
  for (const field of extraction.fields ?? []) {
    const key = canonicalKey(field.key);
    if (key in values) values[key] = valueToString(field.value);
  }
  for (const [rawKey, value] of Object.entries(extraction.cbc ?? {})) {
    const key = canonicalKey(rawKey);
    if (key in values) values[key] = valueToString(value);
  }
  return values;
}

export function parseReviewValues(values: Record<string, string>): {
  cbc: Record<string, number>;
  invalidFields: string[];
} {
  const cbc: Record<string, number> = {};
  const invalidFields: string[] = [];
  for (const field of CBC_REVIEW_FIELDS) {
    const raw = values[field.key]?.trim() ?? "";
    if (!raw) continue;
    const normalized = raw.replace(",", ".");
    if (!/^\d+(?:[.,]\d+)?$/.test(raw)) {
      invalidFields.push(field.label);
      continue;
    }
    const parsed = Number.parseFloat(normalized);
    if (!Number.isFinite(parsed) || parsed < 0) invalidFields.push(field.label);
    else cbc[field.key] = parsed;
  }
  return { cbc, invalidFields };
}
