<script setup lang="ts">
import { onMounted, computed, ref } from "vue"; // Added ref
import { useRouter } from "vue-router";
import { useChatStore, type ChatViewIdentityType } from "@/stores/chat";
import { useAuthStore } from "@/stores/auth";
import ConversationListItem from "@/components/chat/ConversationListItem.vue";
import type { Conversation } from "@/types";

const chatStore = useChatStore();
const authStore = useAuthStore();
const router = useRouter();

const isLoading = computed(() => chatStore.isLoadingConversations);
const error = computed(() => chatStore.error);

// Use the new computed properties for requests and accepted conversations
const pendingRequests = computed(() => {
  return currentViewIdentity.value === "USER"
    ? chatStore.pendingUserRequests
    : chatStore.pendingArtistRequests;
});

const acceptedConversations = computed(() => {
  return currentViewIdentity.value === "USER"
    ? chatStore.acceptedUserConversations
    : chatStore.acceptedArtistConversations;
});

const showRequests = ref(false); // For expanding/collapsing requests

const hasArtistProfile = computed(() => authStore.hasArtistProfile);
const currentViewIdentity = computed({
  get: () => chatStore.currentChatViewIdentity,
  set: (value: ChatViewIdentityType) => {
    chatStore.setActiveChatViewIdentity(value);
    showRequests.value = false; // Reset on view change
  },
});

const openConversation = (conversation: Conversation) => {
  router.push({
    name: "chat-conversation",
    params: { conversationId: conversation.id.toString() },
  });
};

// Deprecated startNewChat
// const startNewChat = () => {
//   router.push({ name: "chat-create" });
// };

onMounted(() => {
  if (authStore.isLoggedIn) {
    chatStore.fetchConversations();
  } else {
    router.push({ name: "login", query: { redirect: "/chat" } });
  }
});
</script>

<template>
  <div class="chat-list-view">
    <div class="chat-header">
      <h2>Direct Messages</h2>
      <!-- Removed New Chat Button -->
    </div>

    <div v-if="hasArtistProfile" class="chat-view-selector">
      <button
        @click="currentViewIdentity = 'USER'"
        :class="{ active: currentViewIdentity === 'USER' }"
      >
        My User DMs
      </button>
      <button
        @click="currentViewIdentity = 'ARTIST'"
        :class="{ active: currentViewIdentity === 'ARTIST' }"
        :disabled="!authStore.artistProfileId"
      >
        My Artist DMs ({{
          authStore.authUser?.profile?.artist_profile_data?.name || "Artist"
        }})
      </button>
    </div>

    <div v-if="isLoading" class="loading-indicator">Loading chats...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div
      v-else-if="
        pendingRequests.length === 0 && acceptedConversations.length === 0
      "
      class="empty-state"
    >
      <p v-if="currentViewIdentity === 'USER'">No user direct messages yet.</p>
      <p v-else>No artist direct messages yet for this profile.</p>
      <p>Start a new conversation by visiting a user or artist profile.</p>
    </div>
    <div v-else>
      <!-- Message Requests Section -->
      <div v-if="pendingRequests.length > 0" class="message-requests-section">
        <button
          @click="showRequests = !showRequests"
          class="requests-toggle-button"
        >
          Message Requests ({{ pendingRequests.length }})
          <span>{{ showRequests ? "▲" : "▼" }}</span>
        </button>
        <div v-if="showRequests" class="conversation-list requests-list">
          <ConversationListItem
            v-for="conversation in pendingRequests"
            :key="`req-${conversation.id}`"
            :conversation="conversation"
            @click="openConversation(conversation)"
          />
        </div>
      </div>

      <!-- Accepted Conversations Section -->
      <h4
        v-if="acceptedConversations.length > 0 && pendingRequests.length > 0"
        class="accepted-chats-header"
      >
        Accepted Chats
      </h4>
      <div
        v-if="
          acceptedConversations.length === 0 &&
          pendingRequests.length > 0 &&
          showRequests
        "
        class="empty-state small-empty"
      >
        No accepted chats yet.
      </div>
      <div class="conversation-list accepted-list">
        <ConversationListItem
          v-for="conversation in acceptedConversations"
          :key="`acc-${conversation.id}`"
          :conversation="conversation"
          @click="openConversation(conversation)"
        />
      </div>
      <div
        v-if="
          acceptedConversations.length === 0 && pendingRequests.length === 0
        "
        class="empty-state"
      >
        No active conversations.
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-list-view {
  max-width: 700px;
  margin: 1rem auto;
  padding: 1rem;
  background-color: var(--color-background-soft);
  border-radius: 8px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}
.chat-header h2 {
  margin: 0;
  color: var(--color-heading);
}

.chat-view-selector {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1rem;
}
.chat-view-selector button {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.9em;
}
.chat-view-selector button.active {
  background-color: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}
.chat-view-selector button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
.empty-state p {
  margin-bottom: 0.5rem;
}
.empty-state.small-empty {
  padding: 1rem;
  font-size: 0.9em;
}

.message-requests-section {
  margin-bottom: 1.5rem;
}
.requests-toggle-button {
  width: 100%;
  padding: 0.75rem 1rem;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  text-align: left;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1em;
  color: var(--color-heading);
}
.requests-toggle-button:hover {
  border-color: var(--color-border-hover);
}
.requests-toggle-button span {
  font-size: 0.8em;
}
.requests-list {
  margin-top: 0.5rem;
  border-left: 2px solid var(--color-accent);
  padding-left: 0.5rem;
}

.accepted-chats-header {
  margin-top: 1.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.9em;
  color: var(--color-text-light);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.conversation-list {
  /* Styles for the list itself, if any */
}
</style>
