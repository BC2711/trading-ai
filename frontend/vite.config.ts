import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    exclude: ["node_modules", "dist", "e2e"],
    css: true
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000"
    }
  }
});
