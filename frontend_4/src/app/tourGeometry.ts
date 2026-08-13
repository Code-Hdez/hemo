import type { TourPlacement } from "./TourContext";

export interface TourRect {
  top: number;
  left: number;
  width: number;
  height: number;
  bottom: number;
  right: number;
}

export interface TourSize {
  width: number;
  height: number;
}

export interface TourLayoutInput {
  viewport: TourSize;
  targetRect: TourRect;
  tooltipSize: TourSize;
  preferredPlacement: TourPlacement;
  bottomInset?: number;
}

export interface TourLayout {
  tooltip: TourRect;
  spotlight: TourRect;
  placement: "top" | "bottom" | "left" | "right";
}

const EDGE_GAP = 16;
const TARGET_PADDING = 8;
const TOOLTIP_GAP = 14;

function clamp(value: number, min: number, max: number): number {
  if (max < min) return min;
  return Math.max(min, Math.min(value, max));
}

function rectFromPosition(left: number, top: number, size: TourSize): TourRect {
  return {
    top,
    left,
    width: size.width,
    height: size.height,
    bottom: top + size.height,
    right: left + size.width,
  };
}

function candidateFits(rect: TourRect, viewport: TourSize, bottomInset: number): boolean {
  return (
    rect.top >= EDGE_GAP &&
    rect.left >= EDGE_GAP &&
    rect.right <= viewport.width - EDGE_GAP &&
    rect.bottom <= viewport.height - bottomInset - EDGE_GAP
  );
}

function clampTooltip(
  left: number,
  top: number,
  tooltipSize: TourSize,
  viewport: TourSize,
  bottomInset: number,
): TourRect {
  const safeBottom = viewport.height - bottomInset - EDGE_GAP;
  return rectFromPosition(
    clamp(left, EDGE_GAP, viewport.width - tooltipSize.width - EDGE_GAP),
    clamp(top, EDGE_GAP, safeBottom - tooltipSize.height),
    tooltipSize,
  );
}

function clampHorizontal(left: number, tooltipSize: TourSize, viewport: TourSize): number {
  return clamp(left, EDGE_GAP, viewport.width - tooltipSize.width - EDGE_GAP);
}

function clampVertical(
  top: number,
  tooltipSize: TourSize,
  viewport: TourSize,
  bottomInset: number,
): number {
  return clamp(top, EDGE_GAP, viewport.height - bottomInset - EDGE_GAP - tooltipSize.height);
}

export function calculateTourLayout({
  viewport,
  targetRect,
  tooltipSize,
  preferredPlacement,
  bottomInset = 0,
}: TourLayoutInput): TourLayout {
  const safeBottom = viewport.height - bottomInset - EDGE_GAP;
  const spotlightLeft = clamp(
    targetRect.left - TARGET_PADDING,
    EDGE_GAP,
    viewport.width - EDGE_GAP,
  );
  const spotlightTop = clamp(targetRect.top - TARGET_PADDING, EDGE_GAP, safeBottom);
  const spotlightRight = clamp(
    targetRect.right + TARGET_PADDING,
    spotlightLeft + EDGE_GAP,
    viewport.width - EDGE_GAP,
  );
  const spotlightBottom = clamp(
    targetRect.bottom + TARGET_PADDING,
    spotlightTop + EDGE_GAP,
    safeBottom,
  );
  const spotlight = rectFromPosition(spotlightLeft, spotlightTop, {
    width: spotlightRight - spotlightLeft,
    height: spotlightBottom - spotlightTop,
  });

  const centeredLeft = spotlight.left + spotlight.width / 2 - tooltipSize.width / 2;
  const topOffset = spotlight.top - tooltipSize.height - TOOLTIP_GAP;
  const bottomOffset = spotlight.bottom + TOOLTIP_GAP;
  const bottom = rectFromPosition(
    clampHorizontal(centeredLeft, tooltipSize, viewport),
    bottomOffset,
    tooltipSize,
  );
  const top = rectFromPosition(
    clampHorizontal(centeredLeft, tooltipSize, viewport),
    topOffset,
    tooltipSize,
  );
  const right = rectFromPosition(
    spotlight.right + TOOLTIP_GAP,
    clampVertical(spotlight.top, tooltipSize, viewport, bottomInset),
    tooltipSize,
  );
  const left = rectFromPosition(
    spotlight.left - tooltipSize.width - TOOLTIP_GAP,
    clampVertical(spotlight.top, tooltipSize, viewport, bottomInset),
    tooltipSize,
  );
  const bottomLeft = rectFromPosition(
    clampHorizontal(spotlight.right - tooltipSize.width, tooltipSize, viewport),
    bottomOffset,
    tooltipSize,
  );

  const clampedBottom = clampTooltip(
    centeredLeft,
    spotlight.bottom + TOOLTIP_GAP,
    tooltipSize,
    viewport,
    bottomInset,
  );
  const clampedTop = clampTooltip(
    centeredLeft,
    spotlight.top - tooltipSize.height - TOOLTIP_GAP,
    tooltipSize,
    viewport,
    bottomInset,
  );
  const clampedRight = clampTooltip(
    spotlight.right + TOOLTIP_GAP,
    spotlight.top,
    tooltipSize,
    viewport,
    bottomInset,
  );
  const clampedLeft = clampTooltip(
    spotlight.left - tooltipSize.width - TOOLTIP_GAP,
    spotlight.top,
    tooltipSize,
    viewport,
    bottomInset,
  );
  const clampedBottomLeft = clampTooltip(
    spotlight.right - tooltipSize.width,
    spotlight.bottom + TOOLTIP_GAP,
    tooltipSize,
    viewport,
    bottomInset,
  );

  const preferredBottomCandidate = preferredPlacement === "bottom-left" ? bottomLeft : bottom;
  const clampedPreferredBottom =
    preferredPlacement === "bottom-left" ? clampedBottomLeft : clampedBottom;

  const ordered =
    preferredPlacement === "right"
      ? [
          ["right", right],
          ["left", left],
          ["bottom", bottom],
          ["top", top],
        ]
      : [
          [
            preferredPlacement === "bottom-left" ? "bottom" : preferredPlacement,
            preferredBottomCandidate,
          ],
          ["top", top],
          ["right", right],
          ["left", left],
        ];
  const clampedOrdered =
    preferredPlacement === "right"
      ? [
          ["right", clampedRight],
          ["left", clampedLeft],
          ["bottom", clampedBottom],
          ["top", clampedTop],
        ]
      : [
          [
            preferredPlacement === "bottom-left" ? "bottom" : preferredPlacement,
            clampedPreferredBottom,
          ],
          ["top", clampedTop],
          ["right", clampedRight],
          ["left", clampedLeft],
        ];

  const [placement, tooltip] =
    ordered.find(([, candidate]) => candidateFits(candidate as TourRect, viewport, bottomInset)) ??
    clampedOrdered.find(([, candidate]) =>
      candidateFits(candidate as TourRect, viewport, bottomInset),
    ) ??
    clampedOrdered[0];

  return {
    tooltip: tooltip as TourRect,
    spotlight,
    placement: placement as TourLayout["placement"],
  };
}
