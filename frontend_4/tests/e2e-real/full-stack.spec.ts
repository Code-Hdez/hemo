import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";

const fixtureDirectory = path.dirname(fileURLToPath(import.meta.url));
const petPhoto = path.resolve(fixtureDirectory, "../../src/assets/luna.png");

test("flujo real de registro, mascota, vigilancia y chat controlado", async ({ page }) => {
  const browserErrors: string[] = [];
  const serverErrors: Array<{ status: number; url: string }> = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 500)
      serverErrors.push({ status: response.status(), url: response.url() });
  });

  const email = `qa-${Date.now()}@hemovet-qa.com`;
  await page.goto("/registro");
  await page.getByLabel("Nombre completo").fill("QA HemoVet");
  await page.getByLabel("Correo electrónico").fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill("QaTest1234");
  await page.getByLabel("Confirmar contraseña").fill("QaTest1234");
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  await expect(page.getByRole("heading", { name: "Cuenta creada" })).toBeVisible();

  await page.getByRole("link", { name: "Ir a iniciar sesión" }).click();
  await page.getByLabel("Correo electrónico").fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill("QaTest1234");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/panel$/);

  await page.goto("/mascotas");
  await page.getByRole("button", { name: "Registrar mascota" }).first().click();
  await page.getByLabel("Nombre").fill("Milo QA");
  await page.getByLabel("Raza").fill("Beagle");
  await page.getByLabel("Zona aproximada").selectOption("do-stgo-santiago");
  await page
    .getByRole("checkbox", {
      name: "Autorizo el uso anónimo y agregado de los hallazgos de esta mascota.",
    })
    .check();
  await page.getByLabel("Seleccionar foto").setInputFiles(petPhoto);
  const photoResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      /\/api\/v1\/pets\/[^/]+\/photo$/.test(response.url()),
  );
  await page.getByRole("button", { name: "Registrar mascota" }).last().click();
  expect((await photoResponse).ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: "Milo QA" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Retrato de Milo QA" }).first()).toHaveAttribute(
    "src",
    /\/api\/v1\/media\/pets\//,
  );

  await page.goto("/vigilancia");
  await expect(
    page.getByRole("heading", { name: /Hallazgos registrados por zona|No hay zonas visibles/ }),
  ).toBeVisible();

  await page.goto("/asistente");
  await page
    .getByPlaceholder("Escribe una pregunta sobre el hemograma...")
    .fill("¿Qué significa WBC?");
  await page.getByRole("button", { name: "Enviar pregunta" }).click();
  await expect(page.getByText(/no esta listo|No fue posible|WBC|leucocitos/i)).toBeVisible();

  expect(browserErrors).toEqual([]);
  expect(serverErrors.filter((error) => !error.url.endsWith("/api/v1/chat"))).toEqual([]);
});
