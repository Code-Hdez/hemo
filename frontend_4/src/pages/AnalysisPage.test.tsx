import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../app/api";
import { AnalysisPage } from "./AnalysisPage";

vi.mock("@tanstack/react-router", async () => {
  const actual =
    await vi.importActual<typeof import("@tanstack/react-router")>("@tanstack/react-router");

  return {
    ...actual,
    Link: ({
      children,
      className,
      to,
    }: {
      children: ReactNode;
      className?: string;
      to: string;
    }) => (
      <a className={className} href={to}>
        {children}
      </a>
    ),
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../app/AuthContext", () => ({
  useAuth: () => ({
    user: null,
  }),
}));

vi.mock("../components/PetFormModal", () => ({
  PetFormModal: () => null,
}));

vi.mock("../app/PetContext", () => ({
  useActivePet: () => ({
    activePet: null,
    activePetId: null,
    setActivePetId: vi.fn(),
    refetch: vi.fn(),
  }),
}));

vi.mock("../app/api", () => ({
  api: {
    analyzeConfirmed: vi.fn(),
    breeds: vi.fn(),
    createPet: vi.fn(),
    extract: vi.fn(),
    uploadPetPhoto: vi.fn(),
  },
}));

function renderAnalysisPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AnalysisPage />
    </QueryClientProvider>,
  );
}

describe("AnalysisPage", () => {
  beforeEach(() => {
    vi.mocked(api.breeds).mockResolvedValue([]);
    vi.mocked(api.analyzeConfirmed).mockResolvedValue({
      id: "tmp-1",
      status: "partial_imputation",
      imputed_fields: [],
      extraction_warnings: [],
      filename: "ingreso-manual",
      file_size: 0,
      created_at: "2026-07-01T00:00:00Z",
      confidence: 1,
      quality_score: 0.9,
      species: "Canina",
      summary: "Resultado temporal para revision.",
      diagnoses: ["Lectura completada"],
      findings: [],
      qc_flags: [],
      lab_values: [],
      persisted: false,
    });
  });

  it("no muestra calidad, confianza ni estado tecnico en el resultado temporal", async () => {
    const user = userEvent.setup();

    renderAnalysisPage();

    await user.click(screen.getByRole("button", { name: "Ingreso manual" }));
    await user.click(screen.getByRole("button", { name: "Comenzar ingreso manual" }));
    await user.type(screen.getByRole("textbox", { name: "Valor de WBC / Leucocitos" }), "12.4");
    await user.type(screen.getByRole("textbox", { name: "Valor de RBC / Eritrocitos" }), "6.2");
    await user.type(screen.getByRole("textbox", { name: "Valor de HGB / Hemoglobina" }), "14.1");
    await user.click(screen.getByRole("button", { name: /Confirmar y analizar/i }));

    const resultHeading = await screen.findByRole("heading", { name: "Lectura completada" });
    const resultSummary = resultHeading.closest(".result-summary");

    expect(resultSummary).not.toBeNull();
    expect(within(resultSummary as HTMLElement).queryByText("Calidad")).not.toBeInTheDocument();
    expect(within(resultSummary as HTMLElement).queryByText("Confianza")).not.toBeInTheDocument();
    expect(within(resultSummary as HTMLElement).queryByText("Estado")).not.toBeInTheDocument();
  });
});
