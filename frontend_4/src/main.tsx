import "@fontsource-variable/lexend";
import "@fontsource-variable/source-sans-3";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AuthProvider } from "./app/AuthContext";
import { PetProvider } from "./app/PetContext";
import { router } from "./app/router";
import { ThemeProvider } from "./app/ThemeContext";
import { TourProvider } from "./app/TourContext";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

async function start(): Promise<void> {
  if (import.meta.env.VITE_ENABLE_MSW === "true") {
    const { worker } = await import("./mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass", quiet: true });
  }

  const root = document.getElementById("root");
  if (!root) throw new Error("No se encontró el contenedor principal.");

  createRoot(root).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <PetProvider>
              <TourProvider>
                <RouterProvider router={router} />
              </TourProvider>
            </PetProvider>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </StrictMode>,
  );
}

void start();
