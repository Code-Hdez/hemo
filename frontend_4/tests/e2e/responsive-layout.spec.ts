import { expect, type Locator, type Page, test } from "@playwright/test";

async function disableTour(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("hemovet4-tour-done", "1");
  });
}

async function authenticateAs(page: Page, token: string): Promise<void> {
  await page.addInitScript((value) => {
    localStorage.setItem("hemovet4-token", value);
    localStorage.setItem("hemovet4-tour-done", "1");
  }, token);
}

async function verticalGap(before: Locator, after: Locator): Promise<number> {
  const [beforeBox, afterBox] = await Promise.all([before.boundingBox(), after.boundingBox()]);
  if (!beforeBox || !afterBox) throw new Error("No fue posible medir las secciones.");
  return afterBox.y - (beforeBox.y + beforeBox.height);
}

async function directChildGaps(page: Page, selector: string): Promise<number[]> {
  return page.locator(selector).evaluate((root) => {
    const children = [...root.children].filter(
      (child) => child instanceof HTMLElement && child.getBoundingClientRect().height > 0,
    );
    return children.slice(1).map((child, index) => {
      const before = children[index].getBoundingClientRect();
      const after = child.getBoundingClientRect();
      return after.top - before.bottom;
    });
  });
}

test("el dashboard invitado separa las métricas de la siguiente sección", async ({ page }) => {
  await disableTour(page);
  await page.setViewportSize({ width: 1024, height: 800 });
  await page.goto("/panel");

  const metrics = page.locator(".dashboard-page > .metric-grid");
  const nextPanel = page.locator(".dashboard-page > .dashboard-panel");
  await expect(metrics).toBeVisible();
  await expect(nextPanel).toBeVisible();

  await expect
    .poll(() => verticalGap(metrics, nextPanel), {
      message: "Las secciones principales deben conservar al menos 16 px de separación.",
    })
    .toBeGreaterThanOrEqual(16);
});

test("vigilancia conserva un ritmo vertical uniforme entre sus secciones", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-spacing");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/vigilancia");
  await expect(page.getByRole("heading", { name: "Datos equivalentes al mapa" })).toBeVisible();

  const gaps = await directChildGaps(page, ".surveillance-page");
  expect(gaps.length).toBeGreaterThan(2);
  for (const gap of gaps) {
    expect(gap).toBeGreaterThanOrEqual(16);
    expect(gap).toBeLessThanOrEqual(22);
  }
});

test("el panel técnico separa todos sus paneles consecutivos", async ({ page }) => {
  await authenticateAs(page, "admin-demo-token");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/panel-tecnico");
  await expect(page.getByRole("heading", { name: "Gates operativos" })).toBeVisible();

  const gaps = await directChildGaps(page, ".technical-page");
  expect(gaps.length).toBeGreaterThan(3);
  for (const gap of gaps) {
    expect(gap).toBeGreaterThanOrEqual(16);
    expect(gap).toBeLessThanOrEqual(22);
  }
});

test("los nombres de archivo largos permanecen dentro del viewport", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-file");
  await page.goto("/analisis/nuevo");

  const filenames = [
    "hemograma.pdf",
    "resultado_paciente_juan_perez.pdf",
    "hemograma_completo_laboratorio_resultados_finales_paciente_con_nombre_muy_largo_2026_version_definitiva.pdf",
    "archivo-con-un-nombre-extremadamente-largo-sin-espacios-ni-separadores-que-podria-romper-el-layout.pdf",
    `${"archivosinseparadores".repeat(12)}.pdf`,
  ];

  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: width <= 390 ? 844 : 1000 });
    for (const name of filenames) {
      await page.locator("#hemogram-file").setInputFiles({
        name,
        mimeType: "application/pdf",
        buffer: Buffer.from("%PDF-1.4 responsive"),
      });

      const widths = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        viewport: document.documentElement.clientWidth,
      }));
      expect(
        widths.page,
        `El archivo "${name}" amplió el documento a ${width}px.`,
      ).toBeLessThanOrEqual(widths.viewport);
      await expect(page.locator(".drop-area strong")).toHaveAttribute("title", name);
      await expect(page.locator(".selected-file strong")).toHaveAttribute("title", name);
    }
  }
});

test("los encabezados aceptan texto dinámico sin separadores", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-heading");
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/mascotas/pet-luna");
  await expect(page.locator(".page-header")).toBeVisible();

  const widths = await page.locator(".page-header").evaluate((header) => {
    const heading = header.querySelector("h1");
    const description = header.querySelector("p:last-child");
    if (!heading || !description) throw new Error("El encabezado no está completo.");
    heading.textContent = "MascotaConNombreExtremadamenteLargoSinSeparadores".repeat(6);
    description.textContent = "DescripcionExtremadamenteLargaSinSeparadores".repeat(8);
    return {
      page: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
      heading: { client: heading.clientWidth, scroll: heading.scrollWidth },
      description: { client: description.clientWidth, scroll: description.scrollWidth },
    };
  });

  expect(widths.page).toBeLessThanOrEqual(widths.viewport);
  expect(widths.heading.scroll).toBeLessThanOrEqual(widths.heading.client);
  expect(widths.description.scroll).toBeLessThanOrEqual(widths.description.client);
});

test("las cards contienen valores y descripciones dinámicas largas", async ({ page }) => {
  await disableTour(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/panel");
  await expect(page.locator(".metric-card").first()).toBeVisible();

  const widths = await page
    .locator(".metric-card")
    .first()
    .evaluate((card) => {
      const value = card.querySelector("strong");
      const detail = card.querySelector("small");
      if (!value || !detail) throw new Error("La card no contiene sus textos esperados.");
      value.textContent = "EstadoExtremadamenteLargoSinSeparadores".repeat(8);
      detail.textContent = "DetalleExtremadamenteLargoSinSeparadores".repeat(8);
      return {
        page: document.documentElement.scrollWidth,
        viewport: document.documentElement.clientWidth,
        card: { client: card.clientWidth, scroll: card.scrollWidth },
      };
    });

  expect(widths.page).toBeLessThanOrEqual(widths.viewport);
  expect(widths.card.scroll).toBeLessThanOrEqual(widths.card.client);
});

test("el chat parte mensajes largos en lugar de recortarlos", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-chat");
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/asistente");

  await page
    .getByPlaceholder("Escribe una pregunta sobre el hemograma...")
    .fill("preguntasinseparadores".repeat(70));
  await page.getByRole("button", { name: "Enviar pregunta" }).click();

  const message = page.locator('.chat-message[data-role="user"] p');
  await expect(message).toBeVisible();
  const widths = await message.evaluate((element) => ({
    page: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
    client: element.clientWidth,
    scroll: element.scrollWidth,
  }));

  expect(widths.page).toBeLessThanOrEqual(widths.viewport);
  expect(widths.scroll).toBeLessThanOrEqual(widths.client);
});

test("la revisión del hemograma usa tablas legibles en laptop compacta", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-review");
  await page.setViewportSize({ width: 1024, height: 800 });
  await page.goto("/analisis/nuevo");
  await page.locator("#hemogram-file").setInputFiles({
    name: "hemograma.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 responsive"),
  });
  await page.getByRole("button", { name: /Extraer valores/ }).click();
  await expect(page.getByRole("heading", { name: "Confirma los valores extraídos" })).toBeVisible();

  const metrics = await page.locator(".review-table-grid").evaluate((grid) => {
    const cards = [...grid.querySelectorAll<HTMLElement>(".review-table-card")];
    return {
      columns: getComputedStyle(grid).gridTemplateColumns.split(" ").filter(Boolean).length,
      cards: cards.map((card) => ({ client: card.clientWidth, scroll: card.scrollWidth })),
    };
  });

  expect(metrics.columns).toBe(1);
  for (const card of metrics.cards) {
    expect(card.scroll).toBeLessThanOrEqual(card.client);
  }
});

test("el cierre del modal invitado permanece dentro del diálogo", async ({ page }) => {
  await disableTour(page);
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo invitado" }).click();

  const dialog = page.getByRole("dialog", { name: "Entrar en modo invitado" });
  const close = dialog.getByRole("button", { name: "Cerrar" });
  await expect(dialog).toBeVisible();
  await expect(close).toBeVisible();

  const [dialogBox, closeBox] = await Promise.all([dialog.boundingBox(), close.boundingBox()]);
  if (!dialogBox || !closeBox) throw new Error("No fue posible medir el modal.");
  expect(closeBox.x).toBeGreaterThanOrEqual(dialogBox.x);
  expect(closeBox.y).toBeGreaterThanOrEqual(dialogBox.y);
  expect(closeBox.x + closeBox.width).toBeLessThanOrEqual(dialogBox.x + dialogBox.width);
  expect(closeBox.y + closeBox.height).toBeLessThanOrEqual(dialogBox.y + dialogBox.height);
});

test("los encabezados de modal conservan visible el botón de cierre", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-dialog");
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Editar a Luna" }).click();

  const dialog = page.getByRole("dialog", { name: "Editar a Luna" });
  await expect(dialog).toBeVisible();
  const metrics = await dialog.evaluate((element) => {
    const header = element.querySelector<HTMLElement>(".dialog__header");
    const heading = header?.querySelector<HTMLElement>("h2");
    const close = header?.querySelector<HTMLElement>(".icon-button");
    if (!header || !heading || !close) throw new Error("El encabezado del modal está incompleto.");
    heading.textContent = "MascotaConNombreExtremadamenteLargoSinSeparadores".repeat(6);
    const dialogBox = element.getBoundingClientRect();
    const closeBox = close.getBoundingClientRect();
    return {
      header: { client: header.clientWidth, scroll: header.scrollWidth },
      closeInside:
        closeBox.left >= dialogBox.left &&
        closeBox.right <= dialogBox.right &&
        closeBox.top >= dialogBox.top &&
        closeBox.bottom <= dialogBox.bottom,
    };
  });

  expect(metrics.header.scroll).toBeLessThanOrEqual(metrics.header.client);
  expect(metrics.closeInside).toBe(true);
});

test("las tablas móviles exponen un área de desplazamiento accesible", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-table");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/vigilancia");

  const region = page.getByRole("region", { name: "Datos tabulares equivalentes al mapa" });
  await expect(region).toBeVisible();
  await expect(region).toHaveAttribute("tabindex", "0");

  const widths = await region.evaluate((element) => ({
    page: document.documentElement.scrollWidth,
    viewport: document.documentElement.clientWidth,
    container: element.clientWidth,
    content: element.scrollWidth,
  }));
  expect(widths.page).toBeLessThanOrEqual(widths.viewport);
  expect(widths.content).toBeGreaterThan(widths.container);
});

test("la navegación móvil reserva espacio solo dentro de la aplicación", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("hemovet4-tour-done", "1"));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  const loginPadding = await page
    .locator("body")
    .evaluate((body) => Number.parseFloat(getComputedStyle(body).paddingBottom));
  expect(loginPadding).toBe(0);

  await page.evaluate(() => {
    localStorage.setItem("hemovet4-token", "owner-completed-token-responsive-nav");
  });
  await page.goto("/panel");
  await expect(page.locator(".mobile-nav")).toBeVisible();
  const clearance = await page.evaluate(() => {
    const workspace = document.querySelector<HTMLElement>(".workspace");
    const mobileNav = document.querySelector<HTMLElement>(".mobile-nav");
    if (!workspace || !mobileNav) throw new Error("La navegación móvil no está disponible.");
    return {
      workspacePadding: Number.parseFloat(getComputedStyle(workspace).paddingBottom),
      navHeight: mobileNav.getBoundingClientRect().height,
    };
  });
  expect(clearance.workspacePadding).toBeGreaterThanOrEqual(clearance.navHeight);
});

test("los controles compactos mantienen objetivos táctiles de 44 px", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-touch");
  await page.setViewportSize({ width: 390, height: 844 });

  await page.goto("/biblioteca");
  const categoryButtons = page.locator(".category-tabs button");
  await expect(categoryButtons.first()).toBeVisible();
  for (const button of await categoryButtons.all()) {
    expect((await button.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44);
  }

  await page.goto("/analisis/nuevo");
  const modeButtons = page.locator(".input-mode-picker button");
  await expect(modeButtons.first()).toBeVisible();
  for (const button of await modeButtons.all()) {
    expect((await button.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44);
  }

  await page.goto("/asistente");
  const suggestion = page.locator(".suggestion-list button").first();
  await expect(suggestion).toBeVisible();
  expect((await suggestion.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44);
});

test("las acciones de modal se apilan en pantallas estrechas", async ({ page }) => {
  await disableTour(page);
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo invitado" }).click();

  const actions = page.locator(".guest-mode-modal .dialog__actions");
  await expect(actions).toBeVisible();
  const dialog = page.getByRole("dialog", { name: "Entrar en modo invitado" });
  const cancel = actions.getByRole("button", { name: "Volver" });
  const primary = actions.getByRole("button", { name: "Continuar como invitado" });
  await expect(cancel).toBeInViewport();
  await expect(primary).toBeInViewport();

  const [dialogBox, cancelBox, primaryBox] = await Promise.all([
    dialog.boundingBox(),
    cancel.boundingBox(),
    primary.boundingBox(),
  ]);
  if (!dialogBox || !cancelBox || !primaryBox) {
    throw new Error("No fue posible medir las acciones del modal.");
  }

  expect(Math.abs(cancelBox.width - primaryBox.width)).toBeLessThanOrEqual(1);
  expect(Math.abs(cancelBox.x - primaryBox.x)).toBeLessThanOrEqual(1);
  expect(primaryBox.y + primaryBox.height).toBeLessThanOrEqual(cancelBox.y);
  expect(cancelBox.y + cancelBox.height).toBeLessThanOrEqual(dialogBox.y + dialogBox.height);
});

test("el sidebar permite desplazamiento en pantallas de poca altura", async ({ page }) => {
  await authenticateAs(page, "owner-completed-token-responsive-sidebar");
  await page.setViewportSize({ width: 390, height: 420 });
  await page.goto("/panel");
  await page.getByRole("button", { name: "Más" }).click();

  const sidebar = page.locator('.sidebar[data-mobile-open="true"]');
  await expect(sidebar).toBeVisible();
  const metrics = await sidebar.evaluate((element) => ({
    overflowY: getComputedStyle(element).overflowY,
    client: element.clientHeight,
    scroll: element.scrollHeight,
  }));
  expect(["auto", "scroll"]).toContain(metrics.overflowY);
  expect(metrics.scroll).toBeGreaterThan(metrics.client);

  await sidebar.evaluate((element) => element.scrollTo({ top: element.scrollHeight }));
  await expect(sidebar.getByRole("button", { name: "Cerrar sesión" })).toBeInViewport();
});

test("las rutas principales no generan scroll horizontal global", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-1440");
  test.setTimeout(90_000);
  await authenticateAs(page, "owner-completed-token-responsive-matrix");

  const allRoutes = [
    "/panel",
    "/analisis/nuevo",
    "/analisis/analysis-luna-jun",
    "/mascotas",
    "/mascotas/pet-luna",
    "/mascotas/pet-luna/historial",
    "/vigilancia",
    "/asistente",
    "/biblioteca",
    "/biblioteca/leucocitos",
    "/cuenta",
    "/limites",
  ];
  const criticalRoutes = [
    "/panel",
    "/analisis/nuevo",
    "/analisis/analysis-luna-jun",
    "/mascotas",
    "/vigilancia",
    "/asistente",
  ];

  await page.goto("/panel");
  await expect(page.locator("#main-content")).toBeVisible();

  for (const width of [320, 390, 768, 1024, 1440, 1920]) {
    await page.setViewportSize({ width, height: width <= 390 ? 844 : 1000 });
    await page.evaluate(
      (dark) => {
        localStorage.setItem("hemovet4-theme", dark ? "dark" : "light");
      },
      width === 390 || width === 1440,
    );

    for (const route of width === 390 || width === 1440 ? allRoutes : criticalRoutes) {
      await page.goto(route);
      await expect(page.locator("#main-content")).toBeVisible();
      await page.waitForTimeout(250);
      const widths = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        viewport: document.documentElement.clientWidth,
      }));
      expect(
        widths.page,
        `${route} generó overflow global con viewport de ${width}px.`,
      ).toBeLessThanOrEqual(widths.viewport);
    }
  }
});

test("login y registro permanecen fluidos en todos los tamaños", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-1440");
  await disableTour(page);

  for (const width of [320, 390, 768, 1024, 1440, 1920]) {
    await page.setViewportSize({ width, height: width <= 390 ? 700 : 1000 });
    for (const route of ["/", "/registro"]) {
      await page.goto(route);
      await expect(page.locator(".auth-screen")).toBeVisible();
      const widths = await page.evaluate(() => ({
        page: document.documentElement.scrollWidth,
        viewport: document.documentElement.clientWidth,
      }));
      expect(
        widths.page,
        `${route} generó overflow global con viewport de ${width}px.`,
      ).toBeLessThanOrEqual(widths.viewport);
    }
  }
});

test("el panel administrativo permanece fluido en todos los tamaños", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "desktop-1440");
  await authenticateAs(page, "admin-demo-token");

  for (const width of [320, 390, 768, 1024, 1440, 1920]) {
    await page.setViewportSize({ width, height: width <= 390 ? 844 : 1000 });
    await page.goto("/panel-tecnico");
    await expect(page.getByRole("heading", { name: "Panel técnico del modelo" })).toBeVisible();
    const widths = await page.evaluate(() => ({
      page: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(
      widths.page,
      `El panel técnico generó overflow global con viewport de ${width}px.`,
    ).toBeLessThanOrEqual(widths.viewport);
  }
});
