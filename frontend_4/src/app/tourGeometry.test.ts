import { describe, expect, it } from "vitest";
import { calculateTourLayout } from "./tourGeometry";

describe("calculateTourLayout", () => {
  it("keeps the tooltip inside the viewport when the target is taller than the screen", () => {
    const layout = calculateTourLayout({
      viewport: { width: 1024, height: 576 },
      targetRect: {
        top: 257.390625,
        left: 539,
        width: 456,
        height: 646.1875,
        bottom: 903.578125,
        right: 995,
      },
      tooltipSize: { width: 320, height: 252 },
      preferredPlacement: "bottom",
    });

    expect(layout.tooltip.top).toBeGreaterThanOrEqual(16);
    expect(layout.tooltip.left).toBeGreaterThanOrEqual(16);
    expect(layout.tooltip.top + layout.tooltip.height).toBeLessThanOrEqual(560);
    expect(layout.tooltip.left + layout.tooltip.width).toBeLessThanOrEqual(1008);
    expect(layout.spotlight.height).toBeLessThanOrEqual(544);
  });

  it("uses the viewport bottom safe area on mobile", () => {
    const layout = calculateTourLayout({
      viewport: { width: 390, height: 844 },
      targetRect: {
        top: 412,
        left: 15,
        width: 360,
        height: 624,
        bottom: 1036,
        right: 375,
      },
      tooltipSize: { width: 320, height: 252 },
      preferredPlacement: "bottom",
      bottomInset: 74,
    });

    expect(layout.tooltip.top + layout.tooltip.height).toBeLessThanOrEqual(754);
    expect(layout.tooltip.left).toBeGreaterThanOrEqual(16);
  });

  it("prefers a non-overlapping top placement when the target is near the desktop bottom edge", () => {
    const layout = calculateTourLayout({
      viewport: { width: 1440, height: 900 },
      targetRect: {
        top: 770.578125,
        left: 539,
        width: 872,
        height: 100,
        bottom: 870.578125,
        right: 1411,
      },
      tooltipSize: { width: 360, height: 251.265625 },
      preferredPlacement: "bottom",
    });

    expect(layout.placement).toBe("top");
    expect(layout.tooltip.bottom).toBeLessThanOrEqual(layout.spotlight.top - 14);
  });

  it("keeps the mobile tooltip above a bottom target when the bottom navigation reduces safe space", () => {
    const layout = calculateTourLayout({
      viewport: { width: 390, height: 844 },
      targetRect: {
        top: 659.21875,
        left: 15,
        width: 360,
        height: 100,
        bottom: 759.21875,
        right: 375,
      },
      tooltipSize: { width: 358, height: 286.0625 },
      preferredPlacement: "bottom",
      bottomInset: 66,
    });

    expect(layout.placement).toBe("top");
    expect(layout.tooltip.bottom).toBeLessThanOrEqual(layout.spotlight.top - 14);
  });
});
