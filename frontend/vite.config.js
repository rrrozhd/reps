import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend mounts brand assets at /assets, and Vite's default output dir is
// also "assets" — that mount is registered first, so bundle requests would 404.
// Emit hashed chunks to /static instead to keep the two namespaces apart.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    assetsDir: "static",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    // `npm run dev` talks to the real backend for API + brand assets.
    proxy: {
      "/api": "http://127.0.0.1:8777",
      "/assets": "http://127.0.0.1:8777",
    },
  },
});
