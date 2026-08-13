import { expect, type Locator, type Page, test } from "@playwright/test";

async function loginAsOwner(page: Page): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Correo electrónico").fill("propietario@hemovet.demo");
  await page.locator('input[type="password"]').fill("Demo1234");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByRole("heading", { name: "Hola, revisemos a Luna" })).toBeVisible();
}

async function navigateInApp(page: Page, path: string): Promise<void> {
  const width = page.viewportSize()?.width ?? 1440;
  let link: Locator;
  if (width <= 700) {
    link = page.locator(`.mobile-nav a[href="${path}"]`).first();
  } else {
    if (width <= 920) {
      const sidebarOpen =
        (await page.locator(".sidebar").getAttribute("data-mobile-open")) === "true";
      if (!sidebarOpen) {
        await page.getByRole("button", { name: "Abrir navegación" }).click();
      }
    }
    link = page.locator(`.sidebar a.sidebar__link[href="${path}"]`).first();
  }
  if ((await link.count()) === 0) {
    await page.getByRole("button", { name: "Abrir navegación" }).click();
    link = page.locator(`.sidebar a.sidebar__link[href="${path}"]`).first();
  }
  await link.click();
  await expect(page).toHaveURL(new RegExp(`${path}$`));
}

test("el resumen del resultado no recorta el estado ni ensancha la página", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/analisis/analysis-luna-jun");
  await expect(page.getByRole("heading", { name: "Resultado orientativo" })).toBeVisible();

  const badge = page.locator(".result-summary__status .status-badge");
  await expect(badge).toBeVisible();

  const dimensions = await badge.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
    pageWidth: document.documentElement.scrollWidth,
    layout: [".main-content", ".result-layout", ".result-main", ".result-summary"].map(
      (selector) => {
        const candidate = document.querySelector<HTMLElement>(selector);
        const rect = candidate?.getBoundingClientRect();
        return { selector, left: rect?.left, right: rect?.right, width: rect?.width };
      },
    ),
    offenders: [...document.querySelectorAll<HTMLElement>("body *")]
      .map((candidate) => {
        const rect = candidate.getBoundingClientRect();
        return {
          className: String(candidate.className).slice(0, 80),
          right: Math.round(rect.right),
          text: candidate.textContent?.trim().slice(0, 60),
        };
      })
      .filter((candidate) => candidate.right > document.documentElement.clientWidth + 1)
      .slice(0, 8),
  }));

  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
  expect(
    dimensions.pageWidth,
    `Layout: ${JSON.stringify(dimensions.layout)}. Elementos fuera del viewport: ${JSON.stringify(dimensions.offenders)}`,
  ).toBeLessThanOrEqual(dimensions.viewportWidth);
});

test("el canvas de vigilancia conserva el ancho del contenedor", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await loginAsOwner(page);
  await page.goto("/vigilancia");
  await expect(
    page.getByRole("heading", { name: "Lo que se observa en tu comunidad" }),
  ).toBeVisible();

  const map = page.locator(".surveillance-map");
  const canvas = page.locator(".surveillance-map .maplibregl-canvas");
  await expect(canvas).toBeVisible();
  await map.evaluate((element) => {
    const panel = element.closest<HTMLElement>(".map-panel");
    if (panel) panel.style.width = "420px";
  });

  await expect
    .poll(async () => {
      const [mapBox, canvasBox] = await Promise.all([map.boundingBox(), canvas.boundingBox()]);
      if (!mapBox || !canvasBox) return Number.POSITIVE_INFINITY;
      return Math.abs(mapBox.width - canvasBox.width);
    })
    .toBeLessThanOrEqual(1);
});

test("la actividad comunitaria usa lenguaje ciudadano y conserva filas legibles", async ({
  page,
}) => {
  await loginAsOwner(page);
  await page.goto("/vigilancia");

  await expect(page.getByText("Reporte poblacional")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Hemogramas registrados en los últimos 90 días" }),
  ).toBeVisible();
  await expect(page.getByText("Semana 21 de 2026")).toBeVisible();
  await expect(page.getByText("1 hemograma", { exact: true })).toBeVisible();

  const rows = page.locator(".temporal-list article");
  await expect(rows).toHaveCount(2);
  for (const row of await rows.all()) {
    const box = await row.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThan(250);
  }
});

test("el formulario de mascota cabe en el viewport y mantiene sus acciones visibles", async ({
  page,
}) => {
  await loginAsOwner(page);
  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Registrar mascota" }).first().click();

  const dialog = page.getByRole("dialog", { name: "Registrar mascota" });
  const actions = dialog.locator(".dialog__actions");
  await expect(dialog).toBeVisible();

  const metrics = await dialog.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return { top: rect.top, bottom: rect.bottom, viewportHeight: window.innerHeight };
  });
  expect(metrics.top).toBeGreaterThanOrEqual(0);
  expect(metrics.bottom).toBeLessThanOrEqual(metrics.viewportHeight);
  await expect(actions).toBeInViewport();
});

test("la búsqueda de residencia alinea el input y su botón", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Registrar mascota" }).first().click();

  const input = page.getByLabel("Buscar dirección o sector");
  const button = page.getByRole("button", { name: "Buscar dirección" });
  const [inputBox, buttonBox] = await Promise.all([input.boundingBox(), button.boundingBox()]);

  expect(inputBox).not.toBeNull();
  expect(buttonBox).not.toBeNull();
  expect(Math.abs((inputBox?.y ?? 0) - (buttonBox?.y ?? 0))).toBeLessThanOrEqual(1);
});

test("orienta al usuario cuando todavía no tiene mascotas", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/mascotas");
  page.on("dialog", (dialog) => dialog.accept());

  await page.getByRole("button", { name: "Eliminar a Luna" }).click();
  await expect(page.getByRole("heading", { name: "Luna" })).toHaveCount(0);
  await page.getByRole("button", { name: "Eliminar a Bruno" }).click();

  await expect(page.getByRole("heading", { name: "Registra tu primera mascota" })).toBeVisible();
  await navigateInApp(page, "/panel");
  await expect(page.getByRole("heading", { name: "Registra tu primera mascota" })).toBeVisible();
  await navigateInApp(page, "/analisis/nuevo");
  await expect(
    page.getByRole("heading", { name: "Necesitas registrar una mascota" }),
  ).toBeVisible();

  await page.evaluate(() => {
    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => {
      if (String(input).includes("/api/v1/epidemiology/points")) {
        return Promise.resolve(
          new Response("[]", { headers: { "Content-Type": "application/json" } }),
        );
      }
      return originalFetch(input, init);
    };
  });
  await navigateInApp(page, "/vigilancia");
  await expect(
    page.getByRole("heading", { name: "No hay zonas visibles en este periodo" }),
  ).toBeVisible();
});

test("presenta un estado útil cuando una mascota aún no tiene hemogramas", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Registrar mascota" }).first().click();

  await page.getByLabel("Nombre").fill("Milo");
  await page.getByLabel("Raza").fill("Beagle");
  await page.getByLabel("Zona aproximada").selectOption("do-stgo-santiago");
  await page
    .getByRole("checkbox", {
      name: "Autorizo el uso anónimo y agregado de los hallazgos de esta mascota.",
    })
    .check();
  await page.getByRole("button", { name: "Registrar mascota" }).last().click();

  const petRow = page.locator(".pet-row").filter({ hasText: "Milo" });
  await expect(petRow).toBeVisible();
  await petRow.getByRole("link", { name: "Ver perfil" }).click();
  await Promise.all([
    page.waitForURL(/\/mascotas\/[^/]+\/historial$/),
    page.getByRole("link", { name: "Abrir historial" }).click(),
  ]);

  await expect(page.getByRole("heading", { name: "Aún no hay hemogramas" })).toBeVisible();
  await expect(page.locator(".history-chart")).toHaveCount(0);
});

test("presenta un error estable cuando una mascota no existe", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/mascotas/pet-inexistente");

  await expect(
    page.getByRole("heading", { name: "No fue posible abrir esta mascota" }),
  ).toBeVisible();
  await expect(page.locator(".loading-state")).toHaveCount(0);
});

test("los datos largos no crean scroll horizontal en móvil", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await loginAsOwner(page);
  await page.goto("/cuenta");
  await page
    .locator(".settings-list dd")
    .nth(1)
    .evaluate((element) => {
      element.textContent = `${"correomuylargosinsegmentos".repeat(8)}@hemovet.demo`;
    });

  let widths = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(widths.page).toBeLessThanOrEqual(widths.viewport);

  await page.goto("/mascotas");
  await page
    .locator(".pet-row")
    .first()
    .evaluate((row) => {
      const name = row.querySelector("h2");
      const notes = row.querySelector(".pet-row__notes p");
      if (name) name.textContent = "MascotaConUnNombreExtremadamenteLargoSinEspacios".repeat(3);
      if (notes) notes.textContent = "NotaPrivadaMuyLargaSinEspacios".repeat(8);
    });

  widths = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
  }));
  expect(widths.page).toBeLessThanOrEqual(widths.viewport);
});

test("el modo demo no genera respuestas 5xx al abrir vigilancia", async ({ page }) => {
  const serverErrors: Array<{ status: number; url: string }> = [];
  page.on("response", (response) => {
    if (response.status() >= 500 && response.url().startsWith("http://127.0.0.1:5175")) {
      serverErrors.push({ status: response.status(), url: response.url() });
    }
  });

  await loginAsOwner(page);
  await page.goto("/vigilancia");
  await expect(page.getByRole("heading", { name: "Hallazgos registrados por zona" })).toBeVisible();
  await page.waitForTimeout(800);

  expect(serverErrors).toEqual([]);
});
