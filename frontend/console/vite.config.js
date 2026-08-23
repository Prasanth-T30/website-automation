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
  // Pinned rather than left to Vite's default, which moves as the "widely
  // available" baseline moves and could silently drop a browser someone is
  // still using. These four cover Safari back to 15.4 — the first release
  // with the dvh units the shell relies on — and the evergreen equivalents.
  build: {
    target: ["es2022", "safari15.4", "chrome109", "firefox115"],
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
    // Absolute, not "./src/test-setup.js". A relative setup path is resolved
    // against the run root rather than this file, and with a sibling copy of
    // the app still present at frontend/ it silently resolved there instead —
    // vitest then reported "no tests" rather than a missing file, which reads
    // like an empty suite instead of a broken one.
    setupFiles: [path.resolve(rootDir, "./src/test-setup.js")],
    globals: true,
  },
});
