import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  css: {
    postcss: "./postcss.config.js",
  },
  server: {
    allowedHosts: ["2837-2406-7400-bb-209f-a177-c9ba-e683-d6db.ngrok-free.app"],
  },
});
