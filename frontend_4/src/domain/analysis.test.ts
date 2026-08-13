import { describe, expect, it } from "vitest";
import {
  buildInitialReviewValues,
  CBC_REVIEW_FIELDS,
  hasEnoughCoreValues,
  parseReviewValues,
  splitReviewFields,
} from "./analysis";

describe("hasEnoughCoreValues", () => {
  it("permite continuar con al menos tres parámetros principales válidos", () => {
    expect(hasEnoughCoreValues({ WBC: 10.2, RBC: 6.1, HGB: 14.7 })).toBe(true);
  });

  it("rechaza valores incompletos o no numéricos", () => {
    expect(hasEnoughCoreValues({ WBC: 10.2, RBC: Number.NaN, NEU: 8.1 })).toBe(false);
  });
});

describe("CBC review fields", () => {
  it("define 24 campos visibles y los divide en dos bloques de 12", () => {
    expect(CBC_REVIEW_FIELDS).toHaveLength(24);
    expect(CBC_REVIEW_FIELDS.map((field) => field.key)).not.toContain("age_years");

    const [left, right] = splitReviewFields(CBC_REVIEW_FIELDS);
    expect(left).toHaveLength(12);
    expect(right).toHaveLength(12);
    expect(left[0]?.key).toBe("WBC");
    expect(right[0]?.key).toBe("PDW");
  });

  it("crea valores iniciales para los 24 campos aunque falten en la extracción", () => {
    const values = buildInitialReviewValues({
      cbc: { WBC: 12.4, Platelets: 230 },
      fields: [],
    });

    expect(Object.keys(values)).toHaveLength(24);
    expect(values.WBC).toBe("12.4");
    expect(values.Platelets).toBe("230");
    expect(values.RBC).toBe("");
  });

  it("convierte inputs editables a CBC numérico sin enviar vacíos", () => {
    const parsed = parseReviewValues({
      WBC: "12,4",
      RBC: "",
      HGB: "14.2",
    });

    expect(parsed).toEqual({ cbc: { WBC: 12.4, HGB: 14.2 }, invalidFields: [] });
  });

  it("rechaza valores negativos o parcialmente numéricos", () => {
    const parsed = parseReviewValues({
      WBC: "12abc",
      RBC: "-6.2",
      HGB: "14.2.1",
      HCT: "42",
    });

    expect(parsed).toEqual({
      cbc: { HCT: 42 },
      invalidFields: ["WBC / Leucocitos", "RBC / Eritrocitos", "HGB / Hemoglobina"],
    });
  });
});
