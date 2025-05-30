<script setup lang="ts">
import { RouterLink, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useCartStore } from "@/stores/cart";
import { computed } from "vue";
import SearchBar from "./SearchBar.vue"; // Import the SearchBar component

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

    <div class="navbar-search">
      <SearchBar />
    </div>

    <div class="navbar-links">
      <RouterLink to="/releases">Releases</RouterLink>
      <RouterLink v-if="authStore.isLoggedIn" to="/library"
        >My Library</RouterLink
      >
      <RouterLink v-if="authStore.isLoggedIn" to="/playlists/my"
        >My Playlists</RouterLink
      >
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
  gap: 1rem; /* Add gap for spacing between sections */
}

.navbar-brand .brand-link {
  font-weight: bold;
  font-size: 1.5rem;
  color: var(--color-heading);
  text-decoration: none;
  margin-right: 1rem; /* Space after brand */
}

.navbar-search {
  flex-grow: 1; /* Allow search bar to take available space */
  display: flex;
  justify-content: center; /* Center search bar if space allows */
  min-width: 250px; /* Minimum width for the search bar container */
  max-width: 500px; /* Maximum width */
}

.navbar-links {
  display: flex; /* Make links align horizontally */
  align-items: center; /* Align items vertically in the center */
}

.navbar-links a,
.navbar-links button {
  margin-left: 1rem;
  text-decoration: none;
  color: var(--color-text);
  background: none;
  border: none;
  cursor: pointer;
  font-size: inherit;
  padding: 0;
}

.navbar-links a.router-link-exact-active {
  font-weight: bold;
  color: var(--color-heading);
}

.navbar-links button.logout-button:hover {
  color: #ff4d4d;
}

.username-display {
  margin-left: 1rem;
  color: var(--color-text);
  font-style: italic;
}

.cart-link {
  position: relative;
}
.cart-count {
  font-size: 0.8em;
  font-weight: bold;
  color: var(--color-accent);
  margin-left: 0.2em;
}

/* Responsive adjustments */
@media (max-width: 992px) {
  /* Adjust breakpoint as needed */
  .navbar-search {
    order: 3; /* Move search to the end on smaller screens */
    width: 100%;
    margin-top: 0.5rem;
    max-width: none;
    justify-content: flex-start;
  }
  .navbar {
    flex-wrap: wrap; /* Allow items to wrap */
  }
  .navbar-links {
    margin-left: 0; /* Reset margin for smaller screens */
    margin-top: 0.5rem; /* Add some space when it wraps */
    width: 100%; /* Take full width if it wraps */
    justify-content: flex-start; /* Align to start when wrapped */
  }
}
@media (max-width: 768px) {
  .navbar-links a,
  .navbar-links button {
    margin-left: 0.75rem;
    font-size: 0.9em;
  }
  .navbar-brand .brand-link {
    font-size: 1.3rem;
  }
}
</style>
