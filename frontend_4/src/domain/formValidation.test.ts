import { describe, expect, it } from "vitest";
import { isRequiredText, isValidProperName, normalizeSingleLineText } from "./formValidation";

describe("validación de formularios", () => {
  it.each([
    "Max",
    "Luna",
    "Niña",
    "Dulce María",
    "Rocky-Jr",
    "O'Neil",
    "Lola’s",
  ])("acepta nombres propios reales: %s", (value) => {
    expect(isValidProperName(value)).toBe(true);
  });

  it.each([
    "Max123",
    "123",
    "Firulais!!!",
    "@@@",
    "🐶",
    "   ",
    "-Max",
    "Max-",
  ])("rechaza nombres con números, símbolos, emojis o espacios inválidos: %s", (value) => {
    expect(isValidProperName(value)).toBe(false);
  });

  it("normaliza espacios externos e internos sin alterar acentos", () => {
    expect(normalizeSingleLineText("  Dulce   María  ")).toBe("Dulce María");
  });

  it("detecta texto obligatorio después de trim", () => {
    expect(isRequiredText("  ")).toBe(false);
    expect(isRequiredText(" Santiago ")).toBe(true);
  });
});
