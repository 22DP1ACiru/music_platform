<script setup lang="ts">
import { RouterLink, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useCartStore } from "@/stores/cart";
import { computed } from "vue";

const authStore = useAuthStore();
const cartStore = useCartStore();
const router = useRouter();

const handleLogout = async () => {
  await authStore.logout(router);
  cartStore.fetchCart();
};

const cartItemCount = computed(() => cartStore.itemCount);
</script>

<template>
  <nav class="navbar">
    <div class="navbar-brand">
      <RouterLink to="/" class="brand-link">Vaultwave</RouterLink>
    </div>
    <div class="navbar-links">
      <RouterLink to="/releases">Releases</RouterLink>
      <RouterLink v-if="authStore.isLoggedIn" to="/library"
        >My Library</RouterLink
      >
      <RouterLink v-if="authStore.isLoggedIn" to="/playlists/my"
        >My Playlists</RouterLink
      >
      <!-- Added My Playlists link -->
      <RouterLink v-if="authStore.isLoggedIn" to="/orders"
        >My Orders</RouterLink
      >
      <RouterLink v-if="authStore.isLoggedIn" to="/chat">Chat</RouterLink>

      <template v-if="!authStore.isLoggedIn">
        <RouterLink to="/login">Login</RouterLink>
        <RouterLink to="/register">Register</RouterLink>
      </template>

      <template v-else>
        <RouterLink to="/cart" class="cart-link" title="Shopping Cart">
          🛒 Cart
          <span v-if="cartItemCount > 0" class="cart-count"
            >({{ cartItemCount }})</span
          >
        </RouterLink>
        <RouterLink
          to="/profile"
          v-if="authStore.authUser"
          class="username-display"
        >
          Hi, {{ authStore.authUser.username }}
        </RouterLink>
        <span v-else class="username-display">Loading...</span>
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

.cart-link {
  position: relative; /* For positioning the count */
}
.cart-count {
  font-size: 0.8em;
  font-weight: bold;
  color: var(--color-accent); /* Or your preferred color for count */
  margin-left: 0.2em;
}
</style>
