import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  base: "/weather-anomaly/",
  worker: { format: "es" },
});
