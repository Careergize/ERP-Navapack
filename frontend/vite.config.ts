import { defineConfig, loadEnv } from "vite";
import { validateHostedDemoConfig } from './scripts/hosted-demo-config.mjs';
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";

// APKs load via file://, so keep asset paths relative
export default defineConfig(({ mode }) => {
  validateHostedDemoConfig(loadEnv(mode, process.cwd(), 'VITE_'));
  return {
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  base: "./",
  server: { port: 5173 },
  };
});
