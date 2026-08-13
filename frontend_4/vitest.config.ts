import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    exclude: ["tests/e2e/**", "tests/e2e-real/**", "node_modules/**", "dist/**"],
    css: true,
  },
});
