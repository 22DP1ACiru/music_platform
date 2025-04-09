<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import LoginForm from "@/components/LoginForm.vue";
import { useAuth } from "@/composables/useAuth";

const { login } = useAuth();
const router = useRouter();
const errorMessage = ref<string | null>(null);
const isLoading = ref(false);

// Define the type for the form data payload
interface LoginPayload {
  username?: string;
  password?: string;
}

const handleLogin = async (payload: LoginPayload) => {
  isLoading.value = true;
  errorMessage.value = null;
  console.log("Logging in user:", payload.username);

  try {
    // Use relative path; baseURL is set in main.ts
    // Send POST request to the token endpoint
    const response = await axios.post("/token/", payload);

    console.log("Login successful:", response.data);

    if (response.data.access && response.data.refresh) {
      localStorage.setItem("accessToken", response.data.access);
      localStorage.setItem("refreshToken", response.data.refresh);
      // --- Normally you'd update a central auth state here ---
      login(response.data.access, response.data.refresh);
      console.log("Tokens stored in localStorage");

      // Redirect to home page after successful login
      alert("Login Successful!"); // Simple feedback
      router.push({ name: "home" });
    } else {
      // Should not happen if API returns 200 OK, but good practice
      throw new Error("Token data missing in response");
    }
  } catch (error: any) {
    console.error("Login failed:", error);
    if (axios.isAxiosError(error) && error.response) {
      // Handle specific errors (e.g., 401 Unauthorized)
      if (error.response.status === 401) {
        errorMessage.value = "Login failed: Invalid username or password.";
      } else {
        // Try to extract specific error messages if available
        const errors = error.response.data;
        if (typeof errors === "object" && errors !== null && errors.detail) {
          errorMessage.value = errors.detail;
        } else {
          errorMessage.value = `Login failed (Status: ${error.response.status}). Please try again.`;
        }
      }
    } else {
      errorMessage.value = "An unexpected network error occurred during login.";
    }
    // Clear potentially stored tokens on failure
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    // --- Normally update auth state here too ---
    // logout();
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="login-page">
    <h2>Login</h2>
    <!-- Use the LoginForm component -->
    <LoginForm @submitLogin="handleLogin" />

    <!-- Display loading/error messages -->
    <p v-if="isLoading">Logging in...</p>
    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

    <p>
      Don't have an account?
      <router-link to="/register">Register here</router-link>
    </p>
  </div>
</template>

<style scoped>
.login-page {
  max-width: 400px;
  margin: 2rem auto;
  padding: 2rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.error-message {
  color: red;
  margin-top: 1rem;
}
</style>
