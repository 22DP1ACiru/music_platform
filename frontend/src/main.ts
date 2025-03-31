import './assets/main.css' // Or your main CSS entry point

import { createApp } from 'vue'
import App from './App.vue'
import router from './router' // Assuming you set up Vue Router (Vite usually includes it)

// Optional: Configure Axios globally
import axios from 'axios';

// Get the API URL from the environment variable injected by Docker Compose via Vite
// Vite exposes env vars prefixed with VITE_ to the client code via import.meta.env
const apiUrl = import.meta.env.VITE_API_URL;

if (!apiUrl) {
  console.error("Error: VITE_API_URL environment variable is not set!");
} else {
  axios.defaults.baseURL = apiUrl;
  console.log("API Base URL set to:", axios.defaults.baseURL); // For debugging in browser console
}

const app = createApp(App)

app.use(router) // Use Vue Router if you have it set up

app.mount('#app')
