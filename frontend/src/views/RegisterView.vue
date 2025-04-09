<!-- src/views/RegisterView.vue -->
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios"; // Make sure axios is imported
import RegistrationForm from "@/components/RegistrationForm.vue"; // Use '@' alias

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
    // Use the relative path; baseURL is set in main.ts
    const response = await axios.post("/register/", payload);
    console.log("Registration successful:", response.data);

    // Redirect to login page after successful registration
    // Optionally show a success message first
    alert("Registration successful! Please log in."); // Simple feedback for now
    router.push({ name: "login" });
  } catch (error: any) {
    console.error("Registration failed:", error);
    if (axios.isAxiosError(error) && error.response) {
      // Try to extract specific error messages from the backend response
      const errors = error.response.data;
      if (typeof errors === "object" && errors !== null) {
        // Join multiple error messages if they exist
        errorMessage.value = Object.entries(errors)
          .map(
            ([field, messages]) =>
              `${field}: ${(messages as string[]).join(", ")}`
          )
          .join(" | ");
      } else {
        errorMessage.value = "Registration failed. Please check your input.";
      }
    } else {
      errorMessage.value = "An unexpected error occurred during registration.";
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="register-page">
    <h2>Register</h2>
    <RegistrationForm @submitRegistration="handleRegistration" />

    <!-- Display loading/error messages -->
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
