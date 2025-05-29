<script setup lang="ts">
import { ref } from "vue";

// Define reactive variables for form fields
const username = ref("");
const email = ref("");
const password = ref("");
const password2 = ref("");

// Define emits to notify parent component of submission
const emit = defineEmits(["submitRegistration"]);

const handleSubmit = () => {
  emit("submitRegistration", {
    username: username.value,
    email: email.value,
    password: password.value,
    password2: password2.value,
  });
};
</script>

<template>
  <form @submit.prevent="handleSubmit" class="registration-form">
    <div class="form-group">
      <label for="reg-username">Username:</label>
      <input type="text" id="reg-username" v-model="username" required />
    </div>
    <div class="form-group">
      <label for="reg-email">Email:</label>
      <input type="email" id="reg-email" v-model="email" required />
    </div>
    <div class="form-group">
      <label for="reg-password">Password:</label>
      <input type="password" id="reg-password" v-model="password" required />
    </div>
    <div class="form-group">
      <label for="reg-password2">Confirm Password:</label>
      <input type="password" id="reg-password2" v-model="password2" required />
    </div>
    <button type="submit">Register</button>
  </form>
</template>

<style scoped>
.registration-form .form-group {
  margin-bottom: 1rem;
  text-align: left;
}
.registration-form label {
  display: block;
  margin-bottom: 0.3rem;
}
.registration-form input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
}
button {
  padding: 0.7rem 1.5rem;
}
</style>
