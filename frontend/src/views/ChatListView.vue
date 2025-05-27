<script setup lang="ts">
import { onMounted, computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useChatStore } from "@/stores/chat";
import { useAuthStore } from "@/stores/auth";
import type { Conversation, CreateMessagePayload } from "@/types"; // Assuming User type is also in types
import ConversationListItem from "@/components/chat/ConversationListItem.vue"; // Path to be created

const chatStore = useChatStore();
const authStore = useAuthStore();
const router = useRouter();

const showNewMessageModal = ref(false);
const newMessageRecipientType = ref<"user" | "artist">("user");
const newMessageRecipientId = ref<number | null>(null); // For user or artist ID
const newMessageText = ref("");
const newMessageError = ref<string | null>(null);

const activeTab = ref<"user" | "artist">("user");

onMounted(() => {
  if (authStore.isLoggedIn) {
    chatStore.fetchConversations();
  } else {
    router.push({ name: "login", query: { redirect: "/chat" } });
  }
});

const sortedUserDMs = computed(() =>
  [...chatStore.userDirectMessages].sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )
);

const sortedArtistDMs = computed(() =>
  [...chatStore.artistDirectMessages].sort(
    (a, b) =>
      new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )
);

const handleOpenNewMessageModal = (type: "user" | "artist") => {
  newMessageRecipientType.value = type;
  newMessageRecipientId.value = null;
  newMessageText.value = "";
  newMessageError.value = null;
  showNewMessageModal.value = true;
};

const handleSendNewMessage = async () => {
  if (!newMessageRecipientId.value || !newMessageText.value.trim()) {
    newMessageError.value = "Recipient ID and message text are required.";
    return;
  }
  newMessageError.value = null;

  const payload: CreateMessagePayload = {
    text: newMessageText.value.trim(),
    message_type: "TEXT", // Default to text for this simple modal
  };

  if (newMessageRecipientType.value === "user") {
    payload.recipient_user_id = newMessageRecipientId.value;
  } else {
    payload.recipient_artist_id = newMessageRecipientId.value;
  }

  const newConversation = await chatStore.sendInitialMessage(payload);
  if (newConversation) {
    showNewMessageModal.value = false;
    router.push({
      name: "chat-conversation",
      params: { conversationId: newConversation.id },
    });
  } else {
    newMessageError.value = chatStore.error || "Failed to send new message.";
  }
};

const navigateToConversation = (conversationId: number) => {
  router.push({
    name: "chat-conversation",
    params: { conversationId },
  });
};
</script>

<template>
  <div class="chat-list-view">
    <h2>Messages</h2>

    <div class="new-message-actions">
      <button @click="handleOpenNewMessageModal('user')">
        New Message to User
      </button>
      <button
        v-if="authStore.hasArtistProfile"
        @click="handleOpenNewMessageModal('artist')"
      >
        New Message to Artist
      </button>
    </div>

    <div class="tabs" v-if="authStore.hasArtistProfile">
      <button
        :class="{ active: activeTab === 'user' }"
        @click="activeTab = 'user'"
      >
        My DMs
      </button>
      <button
        :class="{ active: activeTab === 'artist' }"
        @click="activeTab = 'artist'"
      >
        Artist DMs ({{
          authStore.authUser?.profile?.artist_profile_data?.name ||
          "Your Artist"
        }})
      </button>
    </div>

    <div v-if="chatStore.isLoadingConversations" class="loading">
      Loading conversations...
    </div>
    <div v-else-if="chatStore.error" class="error-message">
      {{ chatStore.error }}
    </div>

    <div v-else>
      <div
        v-show="activeTab === 'user' || !authStore.hasArtistProfile"
        class="conversation-list user-dms"
      >
        <h3 v-if="authStore.hasArtistProfile">My Direct Messages</h3>
        <div
          v-if="sortedUserDMs.length === 0 && !chatStore.isLoadingConversations"
          class="empty-list"
        >
          No direct messages yet.
        </div>
        <ConversationListItem
          v-for="convo in sortedUserDMs"
          :key="convo.id"
          :conversation="convo"
          @click="navigateToConversation(convo.id)"
        />
      </div>

      <div
        v-if="authStore.hasArtistProfile"
        v-show="activeTab === 'artist'"
        class="conversation-list artist-dms"
      >
        <h3>Artist Direct Messages</h3>
        <div
          v-if="
            sortedArtistDMs.length === 0 && !chatStore.isLoadingConversations
          "
          class="empty-list"
        >
          No artist messages yet.
        </div>
        <ConversationListItem
          v-for="convo in sortedArtistDMs"
          :key="convo.id"
          :conversation="convo"
          @click="navigateToConversation(convo.id)"
        />
      </div>
    </div>

    <!-- New Message Modal -->
    <div v-if="showNewMessageModal" class="modal-overlay">
      <div class="modal-content">
        <h3>
          New Message to
          {{ newMessageRecipientType === "user" ? "User" : "Artist" }}
        </h3>
        <div class="form-group">
          <label :for="`recipient-${newMessageRecipientType}-id`">
            Recipient
            {{ newMessageRecipientType === "user" ? "User" : "Artist" }} ID:
          </label>
          <input
            type="number"
            :id="`recipient-${newMessageRecipientType}-id`"
            v-model.number="newMessageRecipientId"
            required
          />
        </div>
        <div class="form-group">
          <label for="new-message-text">Message:</label>
          <textarea
            id="new-message-text"
            v-model="newMessageText"
            rows="3"
            required
          ></textarea>
        </div>
        <p v-if="newMessageError" class="error-message modal-error">
          {{ newMessageError }}
        </p>
        <div class="modal-actions">
          <button
            @click="handleSendNewMessage"
            :disabled="chatStore.isSendingMessage"
          >
            {{ chatStore.isSendingMessage ? "Sending..." : "Send" }}
          </button>
          <button
            @click="showNewMessageModal = false"
            :disabled="chatStore.isSendingMessage"
          >
            Cancel
          </button>
        </div>
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
.chat-list-view h2 {
  margin-bottom: 1.5rem;
}
.new-message-actions {
  margin-bottom: 1.5rem;
  display: flex;
  gap: 1rem;
}
.new-message-actions button {
  padding: 0.5em 1em;
}
.tabs {
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}
.tabs button {
  padding: 0.5rem 1rem;
  border: none;
  background-color: transparent;
  cursor: pointer;
  font-size: 1em;
  color: var(--color-text-light);
  border-bottom: 2px solid transparent;
}
.tabs button.active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
  font-weight: bold;
}
.conversation-list {
  margin-top: 1rem;
}
.conversation-list h3 {
  font-size: 1.2em;
  color: var(--color-heading);
  margin-bottom: 0.8rem;
}
.empty-list {
  color: var(--color-text-light);
  padding: 1rem;
  text-align: center;
  font-style: italic;
}
.loading,
.error-message {
  text-align: center;
  padding: 1rem;
  font-style: italic;
}
.error-message {
  color: var(--vt-c-red-dark);
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}
.modal-content {
  background-color: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 450px;
}
.modal-content h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
}
.modal-content .form-group {
  margin-bottom: 1rem;
}
.modal-content label {
  display: block;
  margin-bottom: 0.3rem;
}
.modal-content input,
.modal-content textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
.modal-actions {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
.modal-error {
  font-size: 0.9em;
  margin-top: 0.5rem;
}
</style>
