import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 2,
  use: {
    baseURL: "http://127.0.0.1:5175",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "VITE_ENABLE_MSW=true VITE_CHAT_AVAILABILITY_POLL_MS=1000 npm run dev",
    url: "http://127.0.0.1:5175",
    reuseExistingServer: false,
  },
  projects: [
    {
      name: "desktop-1440",
      use: { ...devices["Desktop Firefox"], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "laptop-1280",
      use: { ...devices["Desktop Firefox"], viewport: { width: 1280, height: 900 } },
    },
    {
      name: "tablet-768",
      use: { ...devices["Desktop Firefox"], viewport: { width: 768, height: 1024 } },
    },
    {
      name: "mobile-390",
      use: { ...devices["Desktop Firefox"], viewport: { width: 390, height: 844 } },
    },
  ],
});
