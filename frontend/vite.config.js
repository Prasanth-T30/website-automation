import path from "node:path";
import { fileURLToPath } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
// vitest/config re-exports Vite's defineConfig with the `test` block supported.
import { defineConfig } from "vitest/config";

// This config is ESM (package.json sets "type": "module"), so __dirname is not
// defined — derive it from the module URL instead.
const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(rootDir, "./src") },
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
    setupFiles: ["./src/test-setup.js"],
    globals: true,
  },
});
