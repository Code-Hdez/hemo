import { expect, type Page, test } from "@playwright/test";

// Steps de contenido (excluye welcome y done)
const CONTENT_STEPS = 6;

async function loginFresh(
  page: Page,
  token = `owner-pending-token-${crypto.randomUUID()}`,
): Promise<void> {
  await page.addInitScript((authToken) => {
    localStorage.setItem("hemovet4-token", authToken);
    localStorage.removeItem("hemovet4-tour-done");
  }, token);
  await page.goto("/panel");
}

async function loginWithTourDone(page: Page): Promise<void> {
  await page.addInitScript((authToken) => {
    localStorage.setItem("hemovet4-token", authToken);
    localStorage.removeItem("hemovet4-tour-done");
  }, `owner-completed-token-${crypto.randomUUID()}`);
  await page.goto("/panel");
  await expect(page.getByRole("heading", { name: "Hola, revisemos a Luna" })).toBeVisible();
}

async function waitForTour(page: Page): Promise<void> {
  await expect(page.getByRole("dialog", { name: "Bienvenido a HemoVet" })).toBeVisible({
    timeout: 8000,
  });
}

// ── Activación automática ────────────────────────────────────────────────────

test("el tour se activa automáticamente al primer login", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);
  await expect(page.locator(".tour-backdrop")).toBeVisible();
  await expect(page.locator(".tour-tooltip")).toBeVisible();
});

test("el tour no aparece si el usuario ya tiene el tutorial completado", async ({ page }) => {
  await loginWithTourDone(page);
  await expect(page.locator(".tour-backdrop")).not.toBeVisible();
  await expect(page.locator(".tour-tooltip")).not.toBeVisible();
});

// ── Paso de bienvenida ───────────────────────────────────────────────────────

test("el paso de bienvenida muestra título y botón Comenzar tour", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  const tooltip = page.locator(".tour-tooltip--center");
  await expect(tooltip).toBeVisible();
  await expect(tooltip.getByRole("heading", { name: "Bienvenido a HemoVet" })).toBeVisible();
  await expect(tooltip.getByRole("button", { name: "Comenzar tour" })).toBeVisible();
  await expect(tooltip.getByRole("button", { name: "Anterior" })).not.toBeVisible();
  await expect(tooltip.getByText(/Módulo \d+ de/)).not.toBeVisible();
});

test("el paso de bienvenida no tiene spotlight en ningún elemento", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await expect(page.locator(".tour-spotlight")).toHaveCount(0);
});

// ── Navegación por módulos ───────────────────────────────────────────────────

test("avanzar navega al panel y resalta las métricas KPI", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Panel de resumen" }),
  ).toBeVisible();
  await expect(page.locator(".tour-tooltip").getByText("Módulo 1 de 6")).toBeVisible();
  await expect(page).toHaveURL(/\/panel/);
  await expect(page.locator(".tour-spotlight")).toBeVisible({ timeout: 2000 });
});

test("el step de análisis navega a /analisis/nuevo y resalta el panel de carga", async ({
  page,
}) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Cargar un hemograma" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/analisis\/nuevo/);
  await expect(page.locator(".tour-spotlight")).toBeVisible({ timeout: 2000 });
});

test("el step de mascotas navega a /mascotas y resalta el botón de registro", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Registrar mascotas" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/mascotas/);
  await expect(page.locator(".tour-spotlight")).toBeVisible({ timeout: 2000 });
});

test("el step de vigilancia navega a /vigilancia", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  for (let i = 0; i < 3; i++) await page.getByRole("button", { name: "Siguiente" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Vigilancia comunitaria" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/vigilancia/);
  await expect(page.locator(".tour-spotlight")).toBeVisible({ timeout: 2000 });
});

test("el step de asistente navega a /asistente y resalta el chat", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Siguiente" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Asistente con IA" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/asistente/);
  await expect(page.locator('[data-tour="asistente-composer"]')).toBeVisible();
  await expect(page.locator(".tour-spotlight")).toBeVisible({ timeout: 2000 });
});

test("el step de biblioteca navega a /biblioteca y resalta la búsqueda", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  for (let i = 0; i < 5; i++) await page.getByRole("button", { name: "Siguiente" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Biblioteca clínica" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/biblioteca/);
  await expect(page.locator(".tour-spotlight")).toBeVisible({ timeout: 2000 });
});

// ── Progreso ─────────────────────────────────────────────────────────────────

test("los puntos de progreso avanzan con cada paso", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  await expect(page.locator(".tour-progress__dot--active")).toHaveCount(1);
  await expect(page.locator(".tour-progress__dot--done")).toHaveCount(0);

  await page.getByRole("button", { name: "Siguiente" }).click();
  await expect(page.locator(".tour-progress__dot--active")).toHaveCount(1);
  await expect(page.locator(".tour-progress__dot--done")).toHaveCount(1);
});

test("el número total de pasos de contenido es correcto", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  await expect(page.locator(".tour-tooltip__eyebrow")).toHaveText(`Módulo 1 de ${CONTENT_STEPS}`);
});

// ── Navegación hacia atrás ───────────────────────────────────────────────────

test("el botón Anterior retrocede al paso anterior y su ruta", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  await page.getByRole("button", { name: "Siguiente" }).click();

  await expect(page).toHaveURL(/\/analisis\/nuevo/);
  await page.getByRole("button", { name: "Anterior" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Panel de resumen" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/panel/);
});

test("el botón Anterior no aparece en el paso de bienvenida", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await expect(page.getByRole("button", { name: "Anterior" })).not.toBeVisible();
});

// ── Saltar tour ──────────────────────────────────────────────────────────────

test("Saltar tour cierra el overlay y persiste el estado", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Saltar tour" }).click();

  await expect(page.locator(".tour-backdrop")).not.toBeVisible();
  await expect(page.locator(".tour-tooltip")).not.toBeVisible();
  await expect(page.locator(".tour-spotlight")).toHaveCount(0);
});

test("Saltar tour no reaparece al recargar", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Saltar tour" }).click();
  await page.reload();
  await page.waitForTimeout(1500);

  await expect(page.locator(".tour-backdrop")).not.toBeVisible();
});

test("hacer click en el backdrop también cierra el tour", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.locator(".tour-backdrop").click({ position: { x: 10, y: 10 } });
  await expect(page.locator(".tour-backdrop")).not.toBeVisible();
});

// ── Paso final ───────────────────────────────────────────────────────────────

test("el paso final muestra ¡Todo listo! y el botón Finalizar", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  for (let i = 0; i < CONTENT_STEPS; i++) {
    await page.getByRole("button", { name: "Siguiente" }).click();
  }

  const tooltip = page.locator(".tour-tooltip--center");
  await expect(tooltip.getByRole("heading", { name: "¡Todo listo!" })).toBeVisible();
  await expect(tooltip.getByRole("button", { name: "Finalizar" })).toBeVisible();
  await expect(page.locator(".tour-spotlight")).toHaveCount(0);
});

test("click en Finalizar cierra el tour, regresa a /panel y persiste estado", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  for (let i = 0; i < CONTENT_STEPS; i++) {
    await page.getByRole("button", { name: "Siguiente" }).click();
  }
  await page.getByRole("button", { name: "Finalizar" }).click();

  await expect(page.locator(".tour-backdrop")).not.toBeVisible();
  await expect(page).toHaveURL(/\/panel/);
  await page.reload();
  await page.waitForTimeout(1200);
  await expect(page.locator(".tour-backdrop")).not.toBeVisible();
});

// ── Relanzar desde /cuenta ───────────────────────────────────────────────────

test("Repetir tutorial desde /cuenta relanza el tour", async ({ page }) => {
  await loginWithTourDone(page);
  await page.goto("/cuenta");

  await page.getByRole("button", { name: "Repetir tutorial" }).click();

  await waitForTour(page);
  await expect(page.locator(".tour-backdrop")).toBeVisible();
});

test("relanzar el tour no reinicia el estado persistido", async ({ page }) => {
  await loginWithTourDone(page);
  await page.goto("/cuenta");

  await page.getByRole("button", { name: "Repetir tutorial" }).click();
  await waitForTour(page);

  await page.getByRole("button", { name: "Saltar tour" }).click();
  await page.reload();
  await page.waitForTimeout(1200);
  await expect(page.locator(".tour-backdrop")).not.toBeVisible();
});

// ── Accesibilidad ─────────────────────────────────────────────────────────────

test("el tooltip tiene role dialog y aria-modal", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  const dialog = page.locator('[role="dialog"]');
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveAttribute("aria-modal", "true");
  await expect(dialog).toHaveAttribute("aria-labelledby", "tour-step-title");
  await expect(dialog).toHaveAttribute("aria-describedby", "tour-step-description");
});

test("al avanzar el spotlight cambia al nuevo objetivo", async ({ page }) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  const firstSpotlight = page.locator(".tour-spotlight");
  await expect(firstSpotlight).toBeVisible({ timeout: 2000 });
  const firstBox = await firstSpotlight.boundingBox();

  await page.getByRole("button", { name: "Siguiente" }).click();
  const nextSpotlight = page.locator(".tour-spotlight");
  await expect(nextSpotlight).toBeVisible({ timeout: 2000 });
  const nextBox = await nextSpotlight.boundingBox();
  expect(nextBox).not.toEqual(firstBox);
});

test("el tooltip y spotlight permanecen dentro del viewport en el paso del asistente", async ({
  page,
}) => {
  await loginFresh(page);
  await waitForTour(page);

  await page.getByRole("button", { name: "Comenzar tour" }).click();
  for (let i = 0; i < 4; i++) await page.getByRole("button", { name: "Siguiente" }).click();

  await expect(
    page.locator(".tour-tooltip").getByRole("heading", { name: "Asistente con IA" }),
  ).toBeVisible();
  const viewport = page.viewportSize();
  if (!viewport) throw new Error("Viewport no disponible.");
  const tooltip = await page.locator(".tour-tooltip").boundingBox();
  const spotlight = await page.locator(".tour-spotlight").boundingBox();
  expect(tooltip).not.toBeNull();
  expect(spotlight).not.toBeNull();
  expect(tooltip?.x).toBeGreaterThanOrEqual(0);
  expect(tooltip?.y).toBeGreaterThanOrEqual(0);
  expect((tooltip?.x ?? 0) + (tooltip?.width ?? 0)).toBeLessThanOrEqual(viewport.width);
  expect((tooltip?.y ?? 0) + (tooltip?.height ?? 0)).toBeLessThanOrEqual(viewport.height);
  expect(spotlight?.x).toBeGreaterThanOrEqual(0);
  expect(spotlight?.y).toBeGreaterThanOrEqual(0);
  expect((spotlight?.x ?? 0) + (spotlight?.width ?? 0)).toBeLessThanOrEqual(viewport.width);
  expect((spotlight?.y ?? 0) + (spotlight?.height ?? 0)).toBeLessThanOrEqual(viewport.height);
});
