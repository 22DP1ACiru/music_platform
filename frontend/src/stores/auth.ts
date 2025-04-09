import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import type { Router } from "vue-router"; // Import Router type for type hinting

interface User {
  id: number;
  username: string;
  email: string;
}

export const useAuthStore = defineStore("auth", () => {
  // --- State ---
  // Initialize state from localStorage
  const accessToken = ref<string | null>(localStorage.getItem("accessToken"));
  const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));
  const user = ref<User | null>(null);
  const isLoading = ref(false); // Loading state specific to auth actions
  const error = ref<string | null>(null); // Error state specific to auth actions

  // --- Getters ---
  // Computed properties become getters
  const isLoggedIn = computed(() => !!accessToken.value);
  const authUser = computed(() => user.value);
  const authLoading = computed(() => isLoading.value);
  const authError = computed(() => error.value);

  // --- Actions ---
  // Functions that modify state become actions

  // Action to fetch user details
  async function fetchUser() {
    if (!accessToken.value) {
      user.value = null;
      return;
    }
    isLoading.value = true;
    error.value = null;
    try {
      // Axios interceptor will add token
      const response = await axios.get<User>("/users/me/");
      user.value = response.data;
      console.log("Auth Store: Fetched user data:", user.value);
    } catch (err: any) {
      console.error("Auth Store: Failed to fetch user data:", err);
      error.value = "Could not fetch user details.";
      user.value = null;
      // Check if the error is 401 Unauthorized (token invalid/expired)
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        // Token is bad, trigger logout or refresh logic
        // For now, just logout
        console.warn(
          "Auth Store: Access token invalid/expired during fetchUser. Logging out."
        );
        await logout(); // Call the logout action (needs router instance if redirecting)
      }
    } finally {
      isLoading.value = false;
    }
  }

  // Action for login
  async function login(
    payload: { username?: string; password?: string },
    router: Router
  ) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post("/token/", payload);
      if (response.data.access && response.data.refresh) {
        localStorage.setItem("accessToken", response.data.access);
        localStorage.setItem("refreshToken", response.data.refresh);
        accessToken.value = response.data.access;
        refreshToken.value = response.data.refresh;
        console.log("Auth Store: Login successful, tokens stored.");
        // Fetch user details after storing tokens
        await fetchUser();
        // Redirect after successful login and user fetch
        if (user.value) {
          // Only redirect if user fetch was successful
          router.push({ name: "home" });
        } else {
          // Handle case where user fetch failed even after successful token retrieval
          error.value = "Login succeeded but failed to fetch user details.";
        }
      } else {
        throw new Error("Token data missing in login response");
      }
    } catch (err: any) {
      console.error("Auth Store: Login failed:", err);
      localStorage.removeItem("accessToken"); // Ensure tokens are cleared on failed login
      localStorage.removeItem("refreshToken");
      accessToken.value = null;
      refreshToken.value = null;
      user.value = null;

      if (axios.isAxiosError(err) && err.response) {
        if (err.response.status === 401) {
          error.value = "Login failed: Invalid username or password.";
        } else {
          const responseData = err.response.data;
          error.value =
            responseData?.detail ||
            `Login failed (Status: ${err.response.status}).`;
        }
      } else {
        error.value = "An unexpected network error occurred during login.";
      }
      // Re-throw the error if the component needs to know login failed
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  // Action for logout
  async function logout(router?: Router) {
    // Make router optional here
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    console.log("Auth Store: Logged Out");
    // Perform redirect IF router instance is provided
    if (router) {
      try {
        await router.push({ name: "login" }); // Redirect to login
      } catch (navError) {
        console.error("Auth Store: Failed to redirect after logout", navError);
        // Fallback or just log if navigation fails
      }
    }
  }

  // Action for registration (calls API, doesn't change auth state directly)
  async function register(payload: any, router: Router) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post("/register/", payload);
      console.log("Auth Store: Registration successful:", response.data);
      // Redirect to login after successful registration
      alert("Registration successful! Please log in."); // Keep simple feedback
      router.push({ name: "login" });
    } catch (err: any) {
      console.error("Auth Store: Registration failed:", err);
      if (axios.isAxiosError(err) && err.response) {
        const errors = err.response.data;
        if (typeof errors === "object" && errors !== null) {
          error.value = Object.entries(errors)
            .map(
              ([field, messages]) =>
                `${field}: ${(messages as string[]).join(", ")}`
            )
            .join(" | ");
        } else {
          error.value = "Registration failed. Please check your input.";
        }
      } else {
        error.value = "An unexpected error occurred during registration.";
      }
      // Re-throw error so component knows registration failed
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  // --- Action to try auto-login on app load ---
  async function tryAutoLogin() {
    console.log("Auth Store: Checking for existing token on load...");
    if (accessToken.value) {
      // Add token verification step here later using /api/token/verify/
      console.log("Auth Store: Token found, attempting to fetch user...");
      await fetchUser();
    } else {
      console.log("Auth Store: No token found.");
    }
  }

  // Return state, getters, and actions
  return {
    // State (refs)
    accessToken,
    refreshToken,
    user,

    // Getters (computed)
    isLoggedIn,
    authUser,
    authLoading,
    authError,

    // Actions (functions)
    login,
    logout,
    fetchUser,
    register,
    tryAutoLogin,
  };
});
