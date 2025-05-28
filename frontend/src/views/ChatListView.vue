<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useChatStore } from "@/stores/chat";
import { useAuthStore } from "@/stores/auth";
import ConversationListItem from "@/components/chat/ConversationListItem.vue";
// Import a component for creating new messages if you have one
// import CreateNewMessageModal from '@/components/chat/CreateNewMessageModal.vue';

const chatStore = useChatStore();
const authStore = useAuthStore();
const router = useRouter();

type ActiveTab = "user" | "artist";
const activeTab = ref<ActiveTab>("user");

// Use computed properties from the store
const userConversations = computed(() => chatStore.userDirectMessages);
const artistConversations = computed(() => chatStore.artistDirectMessages);
const isLoading = computed(() => chatStore.isLoadingConversations);
const errorLoading = computed(() => chatStore.error);

const hasArtistProfile = computed(() => authStore.hasArtistProfile);

const displayedConversations = computed(() => {
  return activeTab.value === "user"
    ? userConversations.value
    : artistConversations.value;
});

const navigateToConversation = (conversationId: number) => {
  router.push({
    name: "chat-conversation",
    params: { conversationId: conversationId.toString() },
  });
};

const switchToTab = (tab: ActiveTab) => {
  if (tab === "artist" && !hasArtistProfile.value) {
    alert("You do not have an artist profile to view artist DMs.");
    return;
  }
  activeTab.value = tab;
};

onMounted(() => {
  chatStore.fetchConversations();
  // If the user doesn't have an artist profile, default to user tab even if artist was last active
  if (activeTab.value === "artist" && !hasArtistProfile.value) {
    activeTab.value = "user";
  }
});

// Watch for login/logout to re-fetch conversations
watch(
  () => authStore.isLoggedIn,
  (isLoggedIn) => {
    if (isLoggedIn) {
      chatStore.fetchConversations();
    } else {
      chatStore.conversations = []; // Clear conversations on logout
    }
  }
);
</script>

<template>
  <div class="chat-list-view">
    <header class="chat-list-header">
      <h2>Direct Messages</h2>
      <div class="tabs" v-if="hasArtistProfile">
        <button
          @click="switchToTab('user')"
          :class="{ active: activeTab === 'user' }"
        >
          My User DMs
        </button>
        <button
          @click="switchToTab('artist')"
          :class="{ active: activeTab === 'artist' }"
          :disabled="!hasArtistProfile"
        >
          My Artist DMs
        </button>
      </div>
      <!-- Add button for initiating new conversation -->
      <button
        @click="router.push({ name: 'chat-create' })"
        class="new-chat-button"
      >
        New Message
      </button>
      <!-- You'll need a route and component for 'chat-create' -->
    </header>

    <div v-if="isLoading" class="loading-indicator">
      Loading conversations...
    </div>
    <div v-else-if="errorLoading" class="error-message">
      {{ errorLoading }}
    </div>
    <div v-else class="conversations-container">
      <div v-if="displayedConversations.length > 0" class="conversation-list">
        <ConversationListItem
          v-for="conv in displayedConversations"
          :key="conv.id"
          :conversation="conv"
          @click="navigateToConversation(conv.id)"
        />
      </div>
      <div v-else class="empty-state">
        <p v-if="activeTab === 'user'">
          No direct messages for your user account yet.
        </p>
        <p v-if="activeTab === 'artist'">
          No direct messages for your artist profile yet.
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-list-view {
  max-width: 800px;
  margin: 1rem auto;
  padding: 1rem;
}

.chat-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.chat-list-header h2 {
  margin: 0;
  font-size: 1.8em;
}

.tabs {
  display: flex;
  gap: 0.5rem;
}

.tabs button {
  padding: 0.5em 1em;
  border: 1px solid var(--color-border);
  background-color: var(--color-background-soft);
  cursor: pointer;
  border-radius: 4px;
  font-size: 0.9em;
}

.tabs button.active {
  background-color: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}

.tabs button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.new-chat-button {
  background-color: var(--color-accent);
  color: white;
  border: none;
  padding: 0.6em 1em;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
}
.new-chat-button:hover {
  background-color: var(--color-accent-hover);
}

.loading-indicator,
.error-message,
.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-light);
}

.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red);
  border-radius: 4px;
}

.conversation-list {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden; /* For child border radius if needed */
}
</style>
