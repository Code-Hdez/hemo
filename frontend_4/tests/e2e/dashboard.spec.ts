import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

async function suppressTour(page: Page): Promise<void> {
  await page.addInitScript(() => localStorage.setItem("hemovet4-tour-done", "1"));
}

async function loginAsOwner(page: Page): Promise<void> {
  // Suppress the onboarding tour so it doesn't interfere with other tests
  await suppressTour(page);
  await page.goto("/");
  await page.getByLabel("Correo electrónico").fill("propietario@hemovet.demo");
  await page.locator('input[type="password"]').fill("Demo1234");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByRole("heading", { name: "Hola, revisemos a Luna" })).toBeVisible();
}

async function loginAsUserWithoutPets(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("hemovet4-tour-done", "1");
    localStorage.setItem("hemovet4-token", "empty-owner-demo-token");
  });
  await page.goto("/panel");
  await expect(
    page.getByRole("heading", { name: "Puedes analizar sin asociar mascota" }),
  ).toBeVisible();
}

function trackClientProblems(page: Page): { consoleErrors: string[]; badRequests: string[] } {
  const consoleErrors: string[] = [];
  const badRequests: string[] = [];
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().includes("Failed to load resource")) {
      consoleErrors.push(message.text());
    }
  });
  page.on("request", (request) => {
    const payload = `${request.url()} ${request.postData() ?? ""}`;
    if (payload.includes("undefined")) badRequests.push(payload);
  });
  return { consoleErrors, badRequests };
}

async function uploadAndReviewHemogram(page: Page): Promise<void> {
  await page.locator('input[type="file"]').setInputFiles({
    name: "hemograma-prueba.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 prototipo hemovet"),
  });
  await page.getByRole("button", { name: /Extraer valores/ }).click();
  await expect(page.getByRole("heading", { name: "Confirma los valores extraídos" })).toBeVisible();
  await expect(page.locator(".review-table input")).toHaveCount(24);
}

async function expectReviewGridColumns(page: Page): Promise<void> {
  const expectedColumns = (page.viewportSize()?.width ?? 1440) <= 920 ? 1 : 2;
  const columnCount = await page
    .locator(".review-table-grid")
    .evaluate(
      (element) => getComputedStyle(element).gridTemplateColumns.split(" ").filter(Boolean).length,
    );
  expect(columnCount).toBe(expectedColumns);
}

async function openResponsiveSidebar(page: Page): Promise<void> {
  const width = page.viewportSize()?.width ?? 1440;
  if (width <= 700) {
    await page.getByRole("button", { name: "Más" }).click();
  } else if (width <= 920) {
    await page.getByRole("button", { name: "Abrir navegación" }).click();
  }
}

async function openSidebarDestination(page: Page, name: string | RegExp): Promise<void> {
  await openResponsiveSidebar(page);
  await page.locator(".sidebar").getByRole("link", { name }).click();
}

test("abre el dashboard protegido y conserva el aviso clínico", async ({ page }) => {
  await loginAsOwner(page);

  await expect(page.getByText(/No reemplaza el juicio ni la evaluación/)).toBeVisible();
  await expect(page.getByText("Hemogramas guardados", { exact: true })).toBeVisible();
  await expect(
    page.locator("#main-content").getByRole("link", { name: "Nuevo hemograma" }),
  ).toBeVisible();
});

test("el banner de seguridad abre límites sin recargar ni bloquear navegación", async ({
  page,
}) => {
  const problems = trackClientProblems(page);
  await loginAsOwner(page);
  let sessionChecksAfterClick = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/v1/auth/me")) sessionChecksAfterClick += 1;
  });

  await page.getByRole("link", { name: "Ver límites" }).click();

  await expect(page).toHaveURL(/\/limites$/);
  await expect(page.getByRole("heading", { name: "Alcance y límites de HemoVet" })).toBeVisible();
  expect(sessionChecksAfterClick).toBe(0);

  await openSidebarDestination(page, "Mascotas");
  await expect(page.getByRole("heading", { name: "Mascotas" })).toBeVisible();
  expect(problems.consoleErrors).toEqual([]);
  expect(problems.badRequests).toEqual([]);
});

test("el login permite confirmar entrada en modo invitado sin crear sesión", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("hemovet4-tour-done", "1");
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Entrar en modo invitado" }).click();

  const dialog = page.getByRole("dialog", { name: "Entrar en modo invitado" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText(/Puedes subir un hemograma/)).toBeVisible();
  await expect(dialog.getByText("No se guardarán datos.")).toBeVisible();
  await expect(dialog.getByText("No tendrás mascotas registradas.")).toBeVisible();
  await expect(dialog.getByText("No tendrás historial personalizado.")).toBeVisible();
  await expect(dialog.getByText("No tendrás acceso al mapa poblacional.")).toBeVisible();
  await expect(dialog.getByText("No tendrás acceso al Chat LLM.")).toBeVisible();

  await dialog.getByRole("button", { name: "Volver" }).click();
  await expect(dialog).toBeHidden();
  await expect(page).toHaveURL(/\/$/);

  await page.getByRole("button", { name: "Entrar en modo invitado" }).click();
  await page.getByRole("button", { name: "Continuar como invitado" }).click();

  await expect(page).toHaveURL(/\/panel$/);
  await expect(
    page.getByRole("heading", { name: "Analiza un hemograma sin crear cuenta" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/panel$/);
  await expect.poll(() => page.evaluate(() => localStorage.getItem("hemovet4-token"))).toBeNull();
});

test("la ruta /login muestra el acceso de modo invitado", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("hemovet4-tour-done", "1");
  });

  await page.goto("/login");

  await expect(
    page.getByRole("heading", { name: "Revisa la información de tu mascota" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Entrar en modo invitado" }).click();
  await expect(page.getByRole("dialog", { name: "Entrar en modo invitado" })).toBeVisible();
});

test("el invitado entra al dashboard y analiza un hemograma temporal", async ({ page }) => {
  const problems = trackClientProblems(page);
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("hemovet4-tour-done", "1");
  });

  await page.goto("/panel");
  await expect(page).toHaveURL(/\/panel$/);
  await expect(
    page.getByRole("heading", { name: "Analiza un hemograma sin crear cuenta" }),
  ).toBeVisible();
  await page
    .locator("#main-content")
    .getByRole("link", { name: /Nuevo hemograma/ })
    .first()
    .click();

  await uploadAndReviewHemogram(page);
  await expectReviewGridColumns(page);
  await expect(page.getByLabel("Valor de MCV / VCM")).toHaveValue("");
  await page.getByLabel("Valor de MCV / VCM").fill("68,2");
  await page.getByRole("button", { name: /Confirmar y analizar/ }).click();

  await expect(page.getByText("Resultado temporal")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("No guardado")).toBeVisible();
  await expect(page).toHaveURL(/\/analisis\/nuevo$/);
  expect(problems.consoleErrors).toEqual([]);
  expect(problems.badRequests).toEqual([]);
});

test("el invitado ve bloqueadas las secciones privadas", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("hemovet4-tour-done", "1");
  });

  for (const route of ["/mascotas", "/vigilancia", "/asistente", "/cuenta"]) {
    await page.goto(route);
    await expect(
      page.getByRole("heading", { name: "Esta función requiere iniciar sesión" }),
    ).toBeVisible();
  }
});

test("un usuario con sesión y sin mascotas analiza sin pet_id", async ({ page }) => {
  const problems = trackClientProblems(page);
  await loginAsUserWithoutPets(page);
  await page
    .locator("#main-content")
    .getByRole("link", { name: /Nuevo hemograma/ })
    .first()
    .click();
  await expect(page.getByRole("heading", { name: "Análisis sin mascota" })).toBeVisible();

  await uploadAndReviewHemogram(page);
  await page.getByRole("button", { name: /Confirmar y analizar/ }).click();

  await expect(page.getByText("Resultado temporal")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("No guardado")).toBeVisible();
  await expect(page.getByText(/no fue asociado a una mascota/i)).toBeVisible();
  expect(problems.consoleErrors).toEqual([]);
  expect(problems.badRequests).toEqual([]);
});

test("persiste el modo oscuro entre recargas", async ({ page }) => {
  await loginAsOwner(page);
  const width = page.viewportSize()?.width ?? 1440;
  if (width <= 700) {
    await openResponsiveSidebar(page);
    await page
      .locator('.sidebar[data-mobile-open="true"]')
      .getByRole("button", {
        name: "Usar tema oscuro",
      })
      .click();
  } else {
    await page.locator(".topbar").getByRole("button", { name: "Usar tema oscuro" }).click();
  }

  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.goto("/panel");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.locator("#main-content")).toBeVisible();
});

test("completa extracción, confirmación y resultado del hemograma", async ({ page }) => {
  await loginAsOwner(page);
  if ((page.viewportSize()?.width ?? 1280) <= 700) {
    await page.getByRole("link", { name: "Analizar" }).click();
  } else if ((page.viewportSize()?.width ?? 1280) <= 920) {
    await openSidebarDestination(page, /Nuevo hemograma/);
  } else {
    await page
      .getByRole("link", { name: /Nuevo hemograma/ })
      .first()
      .click();
  }

  await page.locator('input[type="file"]').setInputFiles({
    name: "hemograma-prueba.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4 prototipo hemovet"),
  });
  await page.getByRole("button", { name: /Extraer valores/ }).click();
  await expect(page.getByRole("heading", { name: "Confirma los valores extraídos" })).toBeVisible();
  await expect(page.locator(".review-table input")).toHaveCount(24);
  await expectReviewGridColumns(page);

  await page.getByRole("button", { name: /Confirmar y analizar/ }).click();
  await expect(page).toHaveURL(/\/analisis\/analysis-/);
  await expect(page.getByRole("heading", { name: "Resultado orientativo" })).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.getByRole("heading", { name: "Qué observó el sistema" })).toBeVisible();
});

test("el asistente rechaza indicaciones clínicas fuera de alcance", async ({ page }) => {
  await loginAsOwner(page);
  await openSidebarDestination(page, "Asistente");

  await page
    .getByPlaceholder("Escribe una pregunta sobre el hemograma...")
    .fill("Dime el diagnóstico y qué medicamento debo darle");
  await page.getByRole("button", { name: "Enviar pregunta" }).click();
  await expect(page.getByText(/No puedo indicar diagnósticos, medicamentos/)).toBeVisible();
  await expect(
    page.getByText("La respuesta es educativa y no sustituye una evaluación veterinaria"),
  ).toBeVisible();
});

test("el chat se degrada y recupera por polling sin recargar la aplicación", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("hemovet4-tour-done", "1");
    localStorage.setItem("hemovet4-token", "owner-chat-recovery-token-e2e");
  });
  let healthChecks = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/v1/chat/health")) healthChecks += 1;
  });

  await page.goto("/asistente");

  await expect(page.getByText("Generación temporalmente en pausa")).toBeVisible();
  const composer = page.getByRole("textbox", { name: "Pregunta para el asistente" });
  await expect(composer).toBeDisabled();
  await expect(composer).toBeEnabled({ timeout: 6_000 });
  await expect(page.getByText("Generación temporalmente en pausa")).toBeHidden();
  expect(healthChecks).toBeGreaterThanOrEqual(3);

  await composer.fill("¿Qué mide un hemograma canino?");
  await page.getByRole("button", { name: "Enviar pregunta" }).click();
  await expect(page.getByText(/Puedo explicar valores y patrones/)).toBeVisible();
});

test("el asistente pinta la respuesta final validada una sola vez, sin duplicar el mensaje", async ({
  page,
}) => {
  await loginAsOwner(page);
  await openSidebarDestination(page, "Asistente");

  await page
    .getByPlaceholder("Escribe una pregunta sobre el hemograma...")
    .fill("__TEST_PROGRESSIVE_STREAM__");
  await page.getByRole("button", { name: "Enviar pregunta" }).click();

  await expect(page.getByText("Generando y validando una respuesta segura…")).toBeVisible();
  await expect(page.getByText("Los leucocitos se muestran de forma progresiva.")).toBeVisible();
  await expect(page.locator('.chat-message[data-role="assistant"]')).toHaveCount(1);
});

test("el asistente mantiene sugerencias y URL específicas para cada contexto", async ({ page }) => {
  await loginAsOwner(page);
  await openSidebarDestination(page, "Asistente");

  await expect(page.getByRole("button", { name: "¿Qué mide un hemograma canino?" })).toBeVisible();
  await page.getByRole("radio", { name: /Hemograma seleccionado/ }).click();
  await expect(
    page.getByRole("button", { name: "¿Qué valores aparecen fuera del rango?" }),
  ).toBeVisible();
  await expect(page).toHaveURL(/scope=selected_hemogram/);
  await expect(page).toHaveURL(/analysis_id=/);

  await page.getByRole("radio", { name: /Historial de hemogramas/ }).click();
  await expect(page.getByRole("button", { name: "¿Qué cambió entre los estudios?" })).toBeVisible();
  await expect(page).toHaveURL(/scope=hemogram_history/);
  await expect(page).not.toHaveURL(/analysis_id=/);
});

test("un 401 aislado del stream mantiene una sesión todavía válida", async ({ page }) => {
  await loginAsOwner(page);
  await openSidebarDestination(page, "Asistente");

  await page
    .getByPlaceholder("Escribe una pregunta sobre el hemograma...")
    .fill("__TEST_STREAM_401__ sesión válida");
  await page.getByRole("button", { name: "Enviar pregunta" }).click();

  await expect(page.getByText("No se pudo autenticar el stream del chat.")).toBeVisible();
  await expect(page).toHaveURL(/\/asistente$/);
});

test("un 401 del stream cierra una sesión confirmada como expirada", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") pageErrors.push(message.text());
  });
  await loginAsOwner(page);
  await openSidebarDestination(page, "Asistente");
  await page.evaluate(() => localStorage.removeItem("hemovet4-token"));

  await page
    .getByPlaceholder("Escribe una pregunta sobre el hemograma...")
    .fill("__TEST_STREAM_401__ sesión expirada");
  await page.getByRole("button", { name: "Enviar pregunta" }).click();

  await expect(page).toHaveURL(/\/asistente$/);
  await expect(
    page.getByRole("heading", { name: "Esta función requiere iniciar sesión" }),
  ).toBeVisible();
  expect(pageErrors).toEqual([]);
});

test("el dashboard principal no tiene violaciones automáticas críticas de accesibilidad", async ({
  page,
}) => {
  await loginAsOwner(page);

  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  expect(results.violations).toEqual([]);
});

test("separa las métricas técnicas para el rol administrador", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Correo electrónico").fill("admin@hemovet.demo");
  await page.locator('input[type="password"]').fill("Demo1234");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();

  await expect(page.getByRole("heading", { name: "Panel técnico del modelo" })).toBeVisible();
  await expect(page.getByText("PR-AUC macro")).toBeVisible();
  await expect(page.getByText("Validación externa")).toBeVisible();
});

test("sube una foto opcional al registrar una mascota", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Registrar mascota" }).last().click();

  await page.getByLabel("Nombre").fill("Milo");
  await page.getByLabel("Raza").fill("Beagle");
  await page.getByLabel("Zona aproximada").selectOption("do-stgo-santiago");
  await page
    .getByRole("checkbox", {
      name: "Autorizo el uso anónimo y agregado de los hallazgos de esta mascota.",
    })
    .check();
  await page.getByLabel("Seleccionar foto").setInputFiles({
    name: "milo.png",
    mimeType: "image/png",
    buffer: Buffer.from("imagen de prueba"),
  });
  await expect(
    page.getByAltText("Vista previa de la foto de perfil de la mascota"),
  ).toHaveAttribute("src", /^blob:/);

  const upload = page.waitForRequest(
    (request) =>
      request.method() === "POST" && /\/api\/v1\/pets\/[^/]+\/photo$/.test(request.url()),
  );
  await page.getByRole("button", { name: "Registrar mascota" }).last().click();
  await upload;
  await expect(page.getByRole("heading", { name: "Milo" })).toBeVisible();
  await expect(page.getByAltText("Retrato de Milo")).toBeVisible();
});

test("valida nombre, campos obligatorios y limpia errores de ubicación en mascota", async ({
  page,
}) => {
  await loginAsOwner(page);
  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Registrar mascota" }).last().click();

  const dialog = page.getByRole("dialog", { name: "Registrar mascota" });
  await expect(dialog.getByText("Nombre (*)")).toBeVisible();
  await expect(dialog.getByText("Raza (*)")).toBeVisible();
  await expect(dialog.getByText("Zona aproximada (*)")).toBeVisible();
  await expect(dialog.getByText("Residencia y vigilancia comunitaria (*)")).toBeVisible();

  await dialog.getByLabel("Nombre").fill("Max123");
  await dialog.getByLabel("Raza").fill("Beagle");
  await dialog.getByRole("button", { name: "Registrar mascota" }).click();

  await expect(dialog.getByText("El nombre no puede contener números ni símbolos.")).toBeVisible();
  await expect(dialog.getByText("La ubicación es obligatoria.")).toBeVisible();
  await expect(
    dialog.getByText("Confirma el consentimiento para registrar la ubicación agregada."),
  ).toBeVisible();

  await dialog.getByLabel("Nombre").fill("Dulce María");
  await expect(dialog.getByText("El nombre no puede contener números ni símbolos.")).toBeHidden();
  await dialog.getByLabel("Zona aproximada").selectOption("do-stgo-santiago");
  await dialog
    .getByRole("checkbox", {
      name: "Autorizo el uso anónimo y agregado de los hallazgos de esta mascota.",
    })
    .check();

  await expect(dialog.getByText("La ubicación es obligatoria.")).toBeHidden();
  await expect(
    dialog.getByText("Confirma el consentimiento para registrar la ubicación agregada."),
  ).toBeHidden();

  const createPet = page.waitForRequest((request) => {
    if (request.method() !== "POST" || !request.url().endsWith("/api/v1/pets")) return false;
    const payload = JSON.parse(request.postData() ?? "{}");
    return payload.name === "Dulce María" && payload.residence_zone_code === "do-stgo-santiago";
  });
  await dialog.getByRole("button", { name: "Registrar mascota" }).click();
  await createPet;
  await expect(page.getByRole("heading", { name: "Dulce María" })).toBeVisible();
});

test("permite marcar una ubicación antes de otorgar consentimiento", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Registrar mascota" }).click();

  const map = page.locator(".residence-map-picker");
  await map.scrollIntoViewIfNeeded();
  await expect(map).toBeVisible();
  const bounds = await map.boundingBox();
  if (!bounds) throw new Error("El selector de residencia no tiene dimensiones.");
  await page.mouse.click(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2);

  await expect(page.getByText(/Zona marcada solo para este formulario/)).toBeVisible();
  await expect(page.locator(".residence-map-pin")).toHaveCount(1);
  await page
    .getByRole("checkbox", {
      name: "Autorizo el uso anónimo y agregado de los hallazgos de esta mascota.",
    })
    .check();
  await expect(page.getByText(/Al guardar se reducirá a una celda aproximada/)).toBeVisible();
});

test("muestra atención veterinaria cercana desde la zona protegida de la mascota", async ({
  page,
}) => {
  const problems = trackClientProblems(page);
  await loginAsOwner(page);
  await page.goto("/mascotas/pet-luna");

  await expect(page.getByRole("heading", { name: "Atención veterinaria cercana" })).toBeVisible();
  const requestPromise = page.waitForRequest((request) => {
    if (
      request.method() !== "POST" ||
      !request.url().endsWith("/api/v1/residence/nearby-veterinary-care")
    ) {
      return false;
    }
    const payload = JSON.parse(request.postData() ?? "{}");
    return payload.pet_id === "pet-luna" && payload.radius_meters === 10_000;
  });
  await page.getByRole("button", { name: "Buscar centros" }).click();
  await requestPromise;

  await expect(page.getByText("2 centros encontrados")).toBeVisible();
  await expect(page.getByText("Centro Veterinario Comunitario")).toBeVisible();
  await expect(
    page.getByRole("link", {
      name: "Abrir Centro Veterinario Comunitario en OpenStreetMap",
    }),
  ).toHaveAttribute("target", "_blank");
  const accessibility = await new AxeBuilder({ page })
    .include(".veterinary-care-panel")
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  expect(problems.consoleErrors).toEqual([]);
  expect(problems.badRequests).toEqual([]);
});

test("muestra las cinco tendencias principales en el historial", async ({ page }) => {
  await loginAsOwner(page);
  await page.goto("/mascotas/pet-luna/historial");

  await expect(page.getByRole("heading", { name: "Salud plaquetaria" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Oxigenación y serie roja" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Defensas e inflamación" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Evolución de Plaquetas" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Evolución de Eritrocitos" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Evolución de Hemoglobina" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Evolución de Hematocrito" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Evolución de Leucocitos" })).toBeVisible();
});
