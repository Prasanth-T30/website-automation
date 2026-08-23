import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Pinned rather than left to Vite's default, which moves as the "widely
  // available" baseline moves and could silently drop a browser someone is
  // still using. These four cover Safari back to 15.4 — the first release
  // with the dvh units the shell relies on — and the evergreen equivalents.
  build: {
    target: ["es2022", "safari15.4", "chrome109", "firefox115"],
  },
  server: {
    port: 5174,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/uploads": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
