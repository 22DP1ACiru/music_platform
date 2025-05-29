<script setup lang="ts">
import { ref } from "vue";

const username = ref("");
const password = ref("");

const emit = defineEmits(["submitLogin"]);

const handleSubmit = () => {
  emit("submitLogin", {
    username: username.value,
    password: password.value,
  });
};
</script>

<template>
  <form @submit.prevent="handleSubmit" class="login-form">
    <div class="form-group">
      <label for="login-username">Username:</label>
      <input type="text" id="login-username" v-model="username" required />
    </div>
    <div class="form-group">
      <label for="login-password">Password:</label>
      <input type="password" id="login-password" v-model="password" required />
    </div>
    <button type="submit">Login</button>
  </form>
</template>

<style scoped>
.login-form .form-group {
  margin-bottom: 1rem;
  text-align: left;
}
.login-form label {
  display: block;
  margin-bottom: 0.3rem;
}
.login-form input {
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
