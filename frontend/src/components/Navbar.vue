<script setup lang="ts">
import { RouterLink, useRouter } from "vue-router";
import { useAuth } from "@/composables/useAuth";

const { isLoggedIn, logout, user } = useAuth();
const router = useRouter();

const handleLogout = () => {
  logout(); // Clear tokens and state
  router.push({ name: "login" }); // Redirect to login page
};
</script>

<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <RouterLink to="/" class="brand-link">Vaultwave</RouterLink>
    </div>
    <div class="navbar-links">
      <!-- Always show About -->
      <RouterLink to="/about">About</RouterLink>

      <!-- Show Login/Register if NOT logged in -->
      <template v-if="!isLoggedIn">
        <RouterLink to="/login">Login</RouterLink>
        <RouterLink to="/register">Register</RouterLink>
      </template>

      <!-- Show Logout/Profile if logged in -->
      <template v-else>
        <span v-if="user" class="username-display"
          >Hi, {{ user.username }}</span
        >
        <!-- Add Profile link later -->
        <!-- <RouterLink to="/profile">Profile</RouterLink> -->
        <button @click="handleLogout" class="logout-button">Logout</button>
      </template>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 2rem;
  background-color: var(--color-background-soft);
}

.navbar-brand .brand-link {
  font-weight: bold;
  font-size: 1.5rem;
  color: var(--color-heading);
  text-decoration: none;
}

.navbar-links a,
.navbar-links button {
  margin-left: 1rem;
  text-decoration: none;
  color: var(--color-text);
  background: none; /* Style button like link */
  border: none;
  cursor: pointer;
  font-size: inherit; /* Match link font size */
  padding: 0; /* Remove default button padding */
}

.navbar-links a.router-link-exact-active {
  font-weight: bold;
  color: var(--color-heading);
}

.navbar-links button.logout-button:hover {
  color: #ff4d4d; /* Example hover effect for logout */
}

.username-display {
  margin-left: 1rem;
  color: var(--color-text);
  font-style: italic;
}
</style>
