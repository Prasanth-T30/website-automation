import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
// vitest/config re-exports Vite's defineConfig with the `test` block typed.
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    // Proxying keeps the browser same-origin in dev, so the httpOnly auth
    // cookies behave exactly as they will in production behind one domain.
    proxy: {
      "/api": {
        target: process.env.VITE_API_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
      "/health": {
        target: process.env.VITE_API_URL ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
    globals: true,
  },
});
