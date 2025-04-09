<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import LoginForm from "@/components/LoginForm.vue";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
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
    // Call the store action, passing the payload and router
    await authStore.login(payload, router);
  } catch (error: any) {
    // Error message is set within the action
    errorMessage.value = authStore.authError || "Login failed.";
    console.error("LoginView: Login action failed", error);
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="login-page">
    <h2>Login</h2>

    <LoginForm @submitLogin="handleLogin" />
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
