import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(), // Basic Vue plugin
    // Add other Vite plugins here if needed (e.g., Vuetify, Components)
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0", // Listen on all network interfaces within the container
    port: 5341, // The port Vite runs on (should match EXPOSE in Dockerfile and ports in docker-compose.yml)
    strictPort: true, // Ensures Vite fails if the port is already in use
    origin: "https://1c5e-89-221-127-190.ngrok-free.app",
    proxy: {
      "/api": {
        target: "http://backend:8102", // Django backend service
        changeOrigin: true,
      },
      "/media": {
        // If Django serves media files
        target: "http://backend:8102",
        changeOrigin: true,
      },
    },
    watch: {
      // Helps with hot module reloading in some Docker/WSL file system scenarios
      usePolling: true,
    },
  },
});
