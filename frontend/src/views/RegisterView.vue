<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import RegistrationForm from "@/components/RegistrationForm.vue";
import { useAuthStore } from "@/stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const errorMessage = ref<string | null>(null);
const isLoading = ref(false);

// Define the type for the form data payload
interface RegistrationPayload {
  username?: string;
  email?: string;
  password?: string;
  password2?: string;
}

const handleRegistration = async (payload: RegistrationPayload) => {
  isLoading.value = true;
  errorMessage.value = null;
  console.log("Registering user:", payload);

  try {
    // Call the store action, passing payload and router
    await authStore.register(payload, router);
  } catch (error: any) {
    // Error message is set within the action
    errorMessage.value = authStore.authError || "Registration failed.";
    console.error("RegisterView: Register action failed", error);
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="register-page">
    <h2>Register</h2>

    <RegistrationForm @submitRegistration="handleRegistration" />
    <p v-if="isLoading">Registering...</p>
    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p>
      Already have an account? <router-link to="/login">Login here</router-link>
    </p>
  </div>
</template>

<style scoped>
.register-page {
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
