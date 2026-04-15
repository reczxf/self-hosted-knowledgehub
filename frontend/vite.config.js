import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  base: "/ui/",
  plugins: [vue()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/healthz": "http://127.0.0.1:8000",
      "/sources": "http://127.0.0.1:8000",
      "/versions": "http://127.0.0.1:8000",
      "/events": "http://127.0.0.1:8000",
      "/jobs": "http://127.0.0.1:8000",
      "/knowledge": "http://127.0.0.1:8000",
      "/search": "http://127.0.0.1:8000",
      "/ingest": "http://127.0.0.1:8000",
      "/conversation": "http://127.0.0.1:8000"
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
