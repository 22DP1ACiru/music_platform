import "./assets/main.css";

import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import axios from "axios";

// --- Axios Configuration ---
// Get the API URL from the environment variable injected by Docker Compose via Vite
// Vite exposes env vars prefixed with VITE_ to the client code via import.meta.env
const apiUrl = import.meta.env.VITE_API_URL;
if (!apiUrl) {
  console.error("Error: VITE_API_URL environment variable is not set!");
} else {
  axios.defaults.baseURL = apiUrl;
  console.log("API Base URL set to:", axios.defaults.baseURL);
}

// Function to get token (reads directly for interceptor simplicity)
const getAuthToken = () => localStorage.getItem("accessToken");

// Add a request interceptor
axios.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
    // Add header ONLY if token exists and request is to our API
    // (prevents sending token to external URLs if you ever use axios for that)
    // Check if config.url exists and is relative (starts with '/') or absolute to our baseURL
    const isApiUrl =
      config.url &&
      (config.url.startsWith("/") ||
        config.url.startsWith(axios.defaults.baseURL || ""));

    if (token && config.headers && isApiUrl) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config; // Continue with the request configuration
  },
  (error) => {
    // Handle request configuration errors
    console.error("Axios request interceptor error:", error);
    return Promise.reject(error);
  }
);

axios.interceptors.response.use(
  (response) => {
    // Any status code that lie within the range of 2xx cause this function to trigger
    // Do nothing, just return response
    return response;
  },
  async (error) => {
    // Any status codes that falls outside the range of 2xx cause this function to trigger
    const originalRequest = error.config;

    // Check if it's a 401 error and not a retry request already
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true; // Mark that we've tried to retry this request
      console.warn("Access token expired or invalid. Attempting refresh...");

      const refreshToken = localStorage.getItem("refreshToken");
      if (!refreshToken) {
        console.error("No refresh token available. Logging out.");
        // Call logout logic from useAuth (needs careful handling if outside component)
        // For simplicity now, maybe just redirect:
        // window.location.href = '/login'; // Force redirect
        return Promise.reject(error); // Reject if no refresh token
      }

      try {
        // Request a new token using the refresh token
        const refreshResponse = await axios.post("/token/refresh/", {
          refresh: refreshToken,
        });

        const newAccessToken = refreshResponse.data.access;
        // Potentially a new refresh token if rotation is enabled
        const newRefreshToken = refreshResponse.data.refresh;

        console.log("Token refresh successful.");
        localStorage.setItem("accessToken", newAccessToken);
        if (newRefreshToken) {
          localStorage.setItem("refreshToken", newRefreshToken);
        }

        // --- Update the auth state (Needs access to the store/composable instance) ---
        // This is tricky outside components. A central store (Pinia) is better.
        // For now, localStorage is updated, but the reactive state isn't.
        // ---------------------------------------------------------------------------

        // Update the Authorization header of the original request
        axios.defaults.headers.common[
          "Authorization"
        ] = `Bearer ${newAccessToken}`;
        if (originalRequest.headers) {
          originalRequest.headers["Authorization"] = `Bearer ${newAccessToken}`;
        }

        // Retry the original request with the new token
        console.log("Retrying original request with new token.");
        return axios(originalRequest);
      } catch (refreshError: any) {
        console.error("Token refresh failed:", refreshError);
        // Refresh token is invalid or expired, log the user out
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        // --- Update the auth state ---
        // logout(); // Call logout from store/composable

        console.error("Logging out due to refresh failure.");
        // Redirect to login
        window.location.href = "/login"; // Or use router if available
        return Promise.reject(refreshError);
      }
    }

    // For other errors, just pass them on
    return Promise.reject(error);
  }
);

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

import { useAuthStore } from "./stores/auth";
const authStore = useAuthStore();
authStore.tryAutoLogin();

app.mount("#app");
