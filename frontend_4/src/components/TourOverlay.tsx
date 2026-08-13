import { useNavigate } from "@tanstack/react-router";
import { type CSSProperties, useEffect, useRef, useState } from "react";
import { useTour } from "../app/TourContext";
import { calculateTourLayout, type TourLayout, type TourRect } from "../app/tourGeometry";

const TARGET_WAIT_MS = 5000;
const FALLBACK_TOOLTIP_SIZE = { width: 360, height: 230 };

function toTourRect(rect: DOMRect): TourRect {
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
    bottom: rect.bottom,
    right: rect.right,
  };
}

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function bottomInset(): number {
  const mobileNav = document.querySelector<HTMLElement>(".mobile-nav");
  if (!mobileNav || window.getComputedStyle(mobileNav).display === "none") return 0;
  return mobileNav.getBoundingClientRect().height;
}

function waitForElement(selector: string, timeoutMs: number): Promise<HTMLElement> {
  const current = document.querySelector<HTMLElement>(selector);
  if (current) return Promise.resolve(current);

  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      observer.disconnect();
      reject(new Error(`No se encontró el objetivo del tour: ${selector}`));
    }, timeoutMs);
    const observer = new MutationObserver(() => {
      const next = document.querySelector<HTMLElement>(selector);
      if (!next) return;
      window.clearTimeout(timeout);
      observer.disconnect();
      resolve(next);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });
}

function focusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((element) => !element.hasAttribute("aria-hidden"));
}

export function TourOverlay(): React.JSX.Element | null {
  const { active, stepIndex, totalSteps, currentStep, next, prev, skip } = useTour();
  const [layout, setLayout] = useState<TourLayout | null>(null);
  const [targetMissing, setTargetMissing] = useState(false);
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const restoreFocusRef = useRef<HTMLElement | null>(null);
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;

  useEffect(() => {
    if (!active || !currentStep.route) return;
    void navigateRef.current({ to: currentStep.route });
  }, [active, currentStep.route]);

  useEffect(() => {
    if (!active) {
      restoreFocusRef.current?.focus?.();
      restoreFocusRef.current = null;
      return;
    }
    restoreFocusRef.current = document.activeElement as HTMLElement | null;
  }, [active]);

  useEffect(() => {
    if (!active) return;
    dialogRef.current?.setAttribute("data-tour-step", currentStep.id);
    const primary = dialogRef.current?.querySelector<HTMLElement>("[data-tour-primary]");
    primary?.focus({ preventScroll: true });
  }, [active, currentStep.id]);

  useEffect(() => {
    if (!active) return;

    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        event.preventDefault();
        skip();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusables = focusableElements(dialogRef.current);
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [active, skip]);

  useEffect(() => {
    setLayout(null);
    setTargetMissing(false);

    if (!active || !currentStep.target || currentStep.placement === "center") return;

    let cancelled = false;
    let targetElement: HTMLElement | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let firstFrame = 0;
    let secondFrame = 0;

    const updateLayout = () => {
      if (cancelled || !targetElement) return;
      const tooltipRect = tooltipRef.current?.getBoundingClientRect();
      const tooltipSize = tooltipRect
        ? { width: tooltipRect.width, height: tooltipRect.height }
        : FALLBACK_TOOLTIP_SIZE;
      setLayout(
        calculateTourLayout({
          viewport: { width: window.innerWidth, height: window.innerHeight },
          targetRect: toTourRect(targetElement.getBoundingClientRect()),
          tooltipSize,
          preferredPlacement: currentStep.placement,
          bottomInset: bottomInset(),
        }),
      );
    };

    const onViewportChange = () => updateLayout();

    void waitForElement(currentStep.target, TARGET_WAIT_MS)
      .then((element) => {
        if (cancelled) return;
        targetElement = element;
        element.scrollIntoView({
          block: "center",
          inline: "center",
          behavior: prefersReducedMotion() ? "auto" : "smooth",
        });
        updateLayout();
        firstFrame = window.requestAnimationFrame(() => {
          if (tooltipRef.current) resizeObserver?.observe(tooltipRef.current);
          updateLayout();
          secondFrame = window.requestAnimationFrame(updateLayout);
        });
        resizeObserver = new ResizeObserver(updateLayout);
        resizeObserver.observe(element);
        window.addEventListener("resize", onViewportChange);
        window.addEventListener("scroll", onViewportChange, true);
      })
      .catch(() => {
        if (!cancelled) setTargetMissing(true);
      });

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      window.cancelAnimationFrame(firstFrame);
      window.cancelAnimationFrame(secondFrame);
      window.removeEventListener("resize", onViewportChange);
      window.removeEventListener("scroll", onViewportChange, true);
    };
  }, [active, currentStep]);

  if (!active) return null;

  const isCenter = currentStep.placement === "center" || targetMissing || !currentStep.target;
  const isFirst = stepIndex === 0;
  const isDone = currentStep.id === "done";
  const contentTotal = totalSteps - 2;
  const contentIndex = stepIndex - 1;
  const shouldRenderTooltip = isCenter || layout !== null;

  const tooltipStyle: CSSProperties | undefined =
    !isCenter && layout
      ? {
          top: `${layout.tooltip.top}px`,
          left: `${layout.tooltip.left}px`,
        }
      : undefined;

  return (
    <>
      <div
        className={`tour-backdrop${layout && !isCenter ? " tour-backdrop--spotlight" : ""}`}
        onClick={skip}
        aria-hidden="true"
      />

      {layout && !isCenter && (
        <div
          className="tour-spotlight"
          style={{
            top: `${layout.spotlight.top}px`,
            left: `${layout.spotlight.left}px`,
            width: `${layout.spotlight.width}px`,
            height: `${layout.spotlight.height}px`,
          }}
          aria-hidden="true"
        />
      )}

      {shouldRenderTooltip && (
        <div
          key={currentStep.id}
          ref={(element) => {
            tooltipRef.current = element;
            dialogRef.current = element;
          }}
          className={`tour-tooltip${isCenter ? " tour-tooltip--center" : ""}`}
          style={tooltipStyle}
          role="dialog"
          aria-modal="true"
          aria-labelledby="tour-step-title"
          aria-describedby="tour-step-description"
        >
          {!isFirst && !isDone && (
            <div className="tour-progress" aria-hidden="true">
              {Array.from({ length: contentTotal }).map((_, i) => (
                <span
                  // biome-ignore lint/suspicious/noArrayIndexKey: static list
                  key={i}
                  className={`tour-progress__dot${
                    i === contentIndex
                      ? " tour-progress__dot--active"
                      : i < contentIndex
                        ? " tour-progress__dot--done"
                        : ""
                  }`}
                />
              ))}
            </div>
          )}

          {!isFirst && !isDone && (
            <p className="tour-tooltip__eyebrow">
              Módulo {contentIndex + 1} de {contentTotal}
            </p>
          )}

          <h2 className="tour-tooltip__title" id="tour-step-title">
            {currentStep.title}
          </h2>
          <p className="tour-tooltip__body" id="tour-step-description">
            {currentStep.description}
          </p>

          <div className="tour-tooltip__actions">
            {!isDone && (
              <button className="tour-tooltip__skip" type="button" onClick={skip}>
                Saltar tour
              </button>
            )}

            {!isFirst && !isDone && (
              <button className="button button--ghost" type="button" onClick={prev}>
                Anterior
              </button>
            )}

            <button
              className="button button--primary"
              type="button"
              onClick={next}
              data-tour-primary
            >
              {isDone ? "Finalizar" : isFirst ? "Comenzar tour" : "Siguiente"}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
