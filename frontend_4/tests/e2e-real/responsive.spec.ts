import { expect, test } from "@playwright/test";

const viewports = [
  { name: "desktop", width: 1440, height: 1000 },
  { name: "laptop", width: 1280, height: 900 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "mobile", width: 390, height: 844 },
];

test("la pantalla de acceso permanece usable en los breakpoints críticos", async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });

  for (const viewport of viewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: "Revisa la información de tu mascota" }),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(
      scrollWidth,
      `${viewport.name} no debe tener desbordamiento horizontal global`,
    ).toBeLessThanOrEqual(viewport.width);
  }

  expect(browserErrors).toEqual([]);
});
