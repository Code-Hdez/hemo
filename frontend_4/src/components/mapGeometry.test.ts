import { describe, expect, it } from "vitest";
import { geographicCircle } from "./mapGeometry";

describe("geographicCircle", () => {
  it("produce un polígono cerrado anclado a coordenadas geográficas", () => {
    const feature = geographicCircle(-70.69, 19.46, 1_200, {
      id: "zona-demo",
      label: "Santiago - zona demo",
      finding: "Patrón inflamatorio",
      reportCount: 3,
      petCount: 3,
      color: "#2f7ca6",
      fillOpacity: 0.23,
    });
    const ring = feature.geometry.coordinates[0];

    expect(ring).toHaveLength(49);
    expect(ring[0]).toEqual(ring.at(-1));
    expect(ring.some(([lng, lat]) => lng !== -70.69 || lat !== 19.46)).toBe(true);
  });
});
