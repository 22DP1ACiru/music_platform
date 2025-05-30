<script setup lang="ts">
import { RouterLink, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useCartStore } from "@/stores/cart";
import { useChatStore } from "@/stores/chat"; // Import ChatStore
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import SearchBar from "./SearchBar.vue";

const authStore = useAuthStore();
const cartStore = useCartStore();
const chatStore = useChatStore(); // Initialize ChatStore
const router = useRouter();

const isUserMenuOpen = ref(false);

const handleLogout = async () => {
  isUserMenuOpen.value = false;
  await authStore.logout(router);
  cartStore.fetchCart();
  chatStore.fetchConversations(); // Fetch/clear conversations on logout/login
};

const cartItemCount = computed(() => cartStore.itemCount);

// Compute total unread chat messages
const totalUnreadChatMessages = computed(() => {
  if (!authStore.isLoggedIn || !chatStore.conversations) return 0;

  // Sum unread_count from all conversations, considering current view identity
  // If you want a global unread count across both user/artist identities:
  // return chatStore.conversations.reduce((sum, convo) => sum + (convo.unread_count || 0), 0);

  // If you want unread count specific to the current view identity (USER or ARTIST):
  // This requires filtering conversations based on chatStore.currentChatViewIdentity
  // For simplicity, let's assume a global unread count for now, or you can refine this logic.
  // The displayedConversations in chatStore already filters by identity.
  // Let's make it sum all unread messages for the logged-in user regardless of active view.
  let unreadSum = 0;
  chatStore.conversations.forEach((convo) => {
    if (convo.unread_count && convo.unread_count > 0) {
      // Ensure messages are actually for the current user and not self-sent
      // This logic might need to be more sophisticated if unread_count on conversation
      // object doesn't perfectly reflect "unread by me".
      // For now, assuming unread_count is accurate from user's perspective.
      unreadSum += convo.unread_count;
    }
  });
  return unreadSum;

  // A potentially more accurate way, if `unread_count` is always from *my* perspective:
  // return chatStore.displayedConversations.reduce((sum, convo) => sum + (convo.unread_count || 0), 0);
});

const closeUserMenu = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (!target.closest(".user-menu-container")) {
    isUserMenuOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener("click", closeUserMenu);
  if (authStore.isLoggedIn) {
    chatStore.fetchConversations(); // Fetch conversations on mount if logged in
  }
});

onUnmounted(() => {
  document.removeEventListener("click", closeUserMenu);
});

// Watch for login/logout to re-fetch conversations
watch(
  () => authStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      chatStore.fetchConversations();
    } else {
      // Chat store should internally clear conversations on logout if subscribed to authStore
    }
  }
);
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
      <RouterLink to="/releases" class="nav-item">Releases</RouterLink>

      <template v-if="!authStore.isLoggedIn">
        <RouterLink to="/login" class="nav-item">Login</RouterLink>
        <RouterLink to="/register" class="nav-item">Register</RouterLink>
      </template>

      <template v-else>
        <RouterLink to="/chat" class="nav-item chat-link" title="Chat">
          💬 Chat
          <span v-if="totalUnreadChatMessages > 0" class="chat-unread-count">{{
            totalUnreadChatMessages
          }}</span>
        </RouterLink>

        <RouterLink to="/cart" class="nav-item cart-link" title="Shopping Cart">
          🛒 Cart
          <span v-if="cartItemCount > 0" class="cart-count">{{
            cartItemCount
          }}</span>
        </RouterLink>

        <!-- User Menu Dropdown -->
        <div class="user-menu-container nav-item">
          <button
            @click.stop="isUserMenuOpen = !isUserMenuOpen"
            class="user-menu-button"
            aria-haspopup="true"
            :aria-expanded="isUserMenuOpen"
          >
            Hi, {{ authStore.authUser?.username || "User" }} ▼
          </button>
          <div v-if="isUserMenuOpen" class="user-dropdown-menu">
            <RouterLink
              to="/profile"
              @click="isUserMenuOpen = false"
              class="dropdown-item"
              >My Profile</RouterLink
            >
            <RouterLink
              to="/library"
              @click="isUserMenuOpen = false"
              class="dropdown-item"
              >My Library</RouterLink
            >
            <RouterLink
              to="/playlists/my"
              @click="isUserMenuOpen = false"
              class="dropdown-item"
              >My Playlists</RouterLink
            >
            <RouterLink
              to="/orders"
              @click="isUserMenuOpen = false"
              class="dropdown-item"
              >My Orders</RouterLink
            >
            <!-- Chat link removed from dropdown -->
            <button @click="handleLogout" class="dropdown-item logout-action">
              Logout
            </button>
          </div>
        </div>
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
  gap: 1rem;
}

.navbar-brand .brand-link {
  font-weight: bold;
  font-size: 1.5rem;
  color: var(--color-heading);
  text-decoration: none;
  margin-right: 1rem;
}

.navbar-search {
  flex-grow: 1;
  display: flex;
  justify-content: center;
  min-width: 200px;
  max-width: 450px;
}

.navbar-links {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.nav-item {
  text-decoration: none;
  color: var(--color-text);
  padding: 0.5rem 0.2rem;
  position: relative;
  background: none;
  border: none;
  cursor: pointer;
  font-size: inherit;
}

.nav-item.router-link-exact-active:not(.user-menu-button) {
  /* Ensure user menu button doesn't get this style from /profile */
  font-weight: bold;
  color: var(--color-heading);
}

.chat-link,
.cart-link {
  display: flex;
  align-items: center;
}
.chat-unread-count,
.cart-count {
  font-size: 0.75em; /* Made smaller */
  font-weight: bold;
  color: var(--vt-c-white); /* White text for better contrast on accent */
  background-color: var(--color-accent); /* Use accent color for badge */
  margin-left: 0.3em; /* Slightly more space */
  padding: 0.1em 0.45em; /* Adjusted padding for roundness */
  border-radius: 10px; /* More rounded */
  line-height: 1; /* Ensure text is centered in badge */
  min-width: 16px; /* Ensure badge has some width even for single digit */
  text-align: center;
}

/* User Menu Specific Styles */
.user-menu-container {
  position: relative;
}

.user-menu-button {
  background: none;
  border: none;
  color: var(--color-text);
  cursor: pointer;
  padding: 0.5rem 0.2rem;
  font-size: inherit;
}
.user-menu-button:hover,
.user-menu-button.nav-item.router-link-exact-active {
  color: var(--color-heading);
}

.user-dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  z-index: 100;
  min-width: 180px;
  padding: 0.5rem 0;
  list-style: none;
  display: flex;
  flex-direction: column;
}

.dropdown-item {
  display: block;
  padding: 0.6rem 1rem;
  text-decoration: none;
  color: var(--color-text);
  white-space: nowrap;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  font-size: 0.95em;
}

.dropdown-item:hover {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
}
.dropdown-item.logout-action:hover {
  background-color: var(--vt-c-red-soft);
  color: var(--vt-c-red-dark);
}

/* Responsive adjustments */
@media (max-width: 992px) {
  .navbar {
    flex-wrap: wrap;
  }
  .navbar-search {
    order: 3;
    width: 100%;
    margin-top: 0.75rem;
    max-width: none;
    justify-content: flex-start;
  }
  .navbar-links {
    margin-left: 0;
    margin-top: 0.75rem;
    width: 100%;
    justify-content: space-around;
    gap: 0.5rem;
  }
  .nav-item {
    padding: 0.5rem;
  }
}
@media (max-width: 768px) {
  .navbar-links {
    flex-direction: column;
    align-items: stretch;
  }
  .nav-item,
  .user-menu-button {
    text-align: center;
    width: 100%;
  }
  .user-dropdown-menu {
    left: 0;
    right: auto;
    width: 100%;
  }
}
</style>
