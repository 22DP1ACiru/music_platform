import "./assets/main.css";

import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import axios from "axios";
import { useAuthStore } from "./stores/auth";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);

const authStore = useAuthStore();

const apiUrl = import.meta.env.VITE_API_URL;
if (!apiUrl) {
  console.error("Error: VITE_API_URL environment variable is not set!");
} else {
  axios.defaults.baseURL = apiUrl;
  console.log("API Base URL set to:", axios.defaults.baseURL);
}

// Request Interceptor (Uses localStorage, could also use authStore.accessToken getter)
axios.interceptors.request.use(
  (config) => {
    // const token = authStore.accessToken; // Alternative using store state directly
    const token = localStorage.getItem("accessToken"); // Keep using localStorage for simplicity here if preferred
    const isApiUrl =
      config.url &&
      (config.url.startsWith("/") ||
        config.url.startsWith(axios.defaults.baseURL || ""));
    if (token && config.headers && isApiUrl) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error("Axios request interceptor error:", error);
    return Promise.reject(error);
  }
);

// Response Interceptor (Modified to use authStore action)
axios.interceptors.response.use(
  (response) => response, // Pass through successful responses
  async (error) => {
    const originalRequest = error.config;

    // Check if it's a 401, not a refresh attempt itself, and not already retried
    if (
      error.response?.status === 401 &&
      originalRequest.url !== "/token/refresh/" &&
      !originalRequest._retry
    ) {
      originalRequest._retry = true;
      console.warn(
        "Interceptor: Access token expired/invalid. Attempting refresh via store action..."
      );

      try {
        // --- Call the Pinia Store Action ---
        const refreshedSuccessfully = await authStore.refreshTokenAction();
        // -----------------------------------

        if (refreshedSuccessfully) {
          console.log(
            "Interceptor: Token refresh successful via store. Retrying original request."
          );
          // Update header for the *original* request before retrying
          // Use the NEW token, preferably read directly after refresh
          const newAccessToken = localStorage.getItem("accessToken"); // Or use a getter from store if available immediately
          if (newAccessToken && originalRequest.headers) {
            originalRequest.headers[
              "Authorization"
            ] = `Bearer ${newAccessToken}`;
          }
          return axios(originalRequest); // Retry original request
        } else {
          // Refresh failed, the store action should have handled logout/state clearing
          console.error(
            "Interceptor: Refresh token action failed. User should be logged out."
          );
          // Redirect happens in the store action (if router is passed) or manually here if needed
          if (window.location.pathname !== "/login") {
            // Avoid redirect loop if already on login
            router.push({ name: "login" }); // Use router instance
          }
          return Promise.reject(error); // Reject the original error
        }
      } catch (storeActionError) {
        // Catch errors from the store action itself (e.g., network error during refresh)
        console.error(
          "Interceptor: Error occurred during store refreshTokenAction:",
          storeActionError
        );
        // Ensure user is logged out / redirected if store action failed unexpectedly
        if (authStore.isLoggedIn) {
          // Double check state
          await authStore.logout(router); // Attempt logout via store
        } else if (window.location.pathname !== "/login") {
          router.push({ name: "login" }); // Fallback redirect
        }
        return Promise.reject(storeActionError); // Reject with the store action error
      }
    }
    // For other errors or if it was already a retry, just pass them on
    return Promise.reject(error);
  }
);

app.use(router);
app.mount("#app");

authStore.tryAutoLogin();
