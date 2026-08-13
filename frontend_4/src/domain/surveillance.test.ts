import { describe, expect, it } from "vitest";
import { formatActivityCount, formatActivityPeriod, intensityLabel } from "./surveillance";

describe("presentación ciudadana de vigilancia", () => {
  it("convierte períodos técnicos en etiquetas legibles", () => {
    expect(formatActivityPeriod("2026-W21")).toBe("Semana 21 de 2026");
    expect(formatActivityPeriod("2026-06")).toBe("Junio de 2026");
  });

  it("usa cantidades e intensidad en lenguaje cotidiano", () => {
    expect(formatActivityCount(1)).toBe("1 hemograma");
    expect(formatActivityCount(3)).toBe("3 hemogramas");
    expect(intensityLabel("moderate")).toBe("Varios registros");
  });
});
