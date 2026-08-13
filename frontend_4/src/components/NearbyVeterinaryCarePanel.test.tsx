import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../app/api";
import type { Pet } from "../domain/types";
import { NearbyVeterinaryCarePanel } from "./NearbyVeterinaryCarePanel";

vi.mock("../app/api", () => ({
  api: {
    nearbyVeterinaryCare: vi.fn(),
  },
}));

const pet: Pet = {
  id: "pet-1",
  owner_id: "owner-1",
  name: "Luna",
  residence_label: "Santiago - zona agregada",
  residence_lat: 19.46,
  residence_lng: -70.69,
  residence_precision: "grid_2km",
  residence_consent: true,
  created_at: "2026-07-01T00:00:00Z",
};

function renderPanel(targetPet: Pet = pet): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <NearbyVeterinaryCarePanel pet={targetPet} />
    </QueryClientProvider>,
  );
}

describe("NearbyVeterinaryCarePanel", () => {
  beforeEach(() => {
    vi.mocked(api.nearbyVeterinaryCare).mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it("busca a petición del usuario y muestra resultados públicos con distancia", async () => {
    vi.mocked(api.nearbyVeterinaryCare).mockResolvedValue({
      items: [
        {
          name: "Clínica Canina",
          lat: 19.47,
          lng: -70.7,
          distance_meters: 1_420,
          address: "Av. Principal",
          osm_url: "https://www.openstreetmap.org/node/123",
        },
      ],
      source: "openstreetmap",
      search_url: "https://www.openstreetmap.org/search?query=veterinaria",
      location_precision: "grid_2km",
      message: "Llama antes de trasladarte.",
    });
    const user = userEvent.setup();
    renderPanel();

    expect(api.nearbyVeterinaryCare).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Buscar centros" }));

    expect(await screen.findByText("Clínica Canina")).toBeVisible();
    expect(screen.getByText("1.4 km desde la zona aproximada")).toBeVisible();
    expect(api.nearbyVeterinaryCare).toHaveBeenCalledWith({
      pet_id: "pet-1",
      radius_meters: 10_000,
    });
    expect(
      screen.getByRole("link", { name: "Abrir Clínica Canina en OpenStreetMap" }),
    ).toHaveAttribute("href", "https://www.openstreetmap.org/node/123");
  });

  it("no permite buscar sin una ubicación aproximada consentida", () => {
    renderPanel({
      ...pet,
      residence_consent: false,
      residence_lat: null,
      residence_lng: null,
    });

    expect(screen.getByRole("button", { name: "Buscar centros" })).toBeDisabled();
    expect(screen.getByText(/Registra y autoriza una zona aproximada/i)).toBeVisible();
  });
});
