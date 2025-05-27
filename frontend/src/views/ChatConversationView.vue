<script setup lang="ts">
import { ref, onMounted, watch, nextTick, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChatStore } from "@/stores/chat";
import { useAuthStore } from "@/stores/auth";
import type { ChatMessage, Conversation } from "@/types";
import ChatMessageItem from "@/components/chat/ChatMessageItem.vue";

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const authStore = useAuthStore();

const newMessageText = ref("");
const newMessageFile = ref<File | null>(null);
const fileInputKey = ref(0);
const messageContainerRef = ref<HTMLElement | null>(null);
const localError = ref<string | null>(null);

const conversationId = computed(() => {
  const idParam = route.params.conversationId;
  return Array.isArray(idParam)
    ? parseInt(idParam[0], 10)
    : parseInt(idParam as string, 10);
});

const activeConversation = computed<Conversation | undefined>(() => {
  if (isNaN(conversationId.value)) return undefined;
  return chatStore.conversations.find((c) => c.id === conversationId.value);
});

const canInteract = computed(() => {
  if (!activeConversation.value) return false;
  return (
    activeConversation.value.is_accepted ||
    (authStore.authUser &&
      activeConversation.value.initiator?.id !== authStore.authUser.id)
  );
});

const showAcceptButton = computed(() => {
  return (
    activeConversation.value &&
    !activeConversation.value.is_accepted &&
    authStore.authUser &&
    activeConversation.value.initiator?.id !== authStore.authUser.id
  );
});

const scrollToBottom = (smooth: boolean = false) => {
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTo({
        top: messageContainerRef.value.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
      });
    }
  });
};

const loadConversationAndMessages = async () => {
  localError.value = null;
  if (isNaN(conversationId.value)) {
    localError.value = "Invalid conversation ID in URL.";
    return;
  }

  // Ensure conversations are loaded first
  if (
    chatStore.conversations.length === 0 &&
    authStore.isLoggedIn &&
    !chatStore.isLoadingConversations
  ) {
    await chatStore.fetchConversations();
  }

  // After attempting to fetch conversations, check if the active one exists
  if (!activeConversation.value) {
    // If still not found, it might be an access issue or genuinely not exist
    // Or the fetchConversations failed.
    if (!chatStore.error) {
      // If there wasn't a general error fetching conversations
      localError.value = "Conversation not found or you do not have access.";
    } else {
      localError.value = chatStore.error; // Show the error from fetching conversations
    }
    chatStore.clearActiveConversation(); // Clear any stale messages
    return; // Stop further execution if conversation is not found
  }

  // If conversation is found, load its messages
  await chatStore.fetchMessagesForConversation(conversationId.value);
  if (chatStore.error && !localError.value) {
    // if fetchMessages had an error
    localError.value = chatStore.error;
  }
  scrollToBottom();
};

onMounted(() => {
  // Clear any previously active conversation data first
  chatStore.clearActiveConversation();
  loadConversationAndMessages();
});

watch(
  () => route.params.conversationId,
  (newIdParam, oldIdParam) => {
    const newId = Array.isArray(newIdParam) ? newIdParam[0] : newIdParam;
    const oldId = Array.isArray(oldIdParam) ? oldIdParam[0] : oldIdParam;
    if (newId && newId !== oldId) {
      chatStore.clearActiveConversation();
      loadConversationAndMessages();
    }
  }
  // No immediate: true here, onMounted handles initial load.
);

watch(
  () => chatStore.activeConversationMessages,
  () => {
    scrollToBottom(true);
  },
  { deep: true }
);

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    newMessageFile.value = target.files[0];
  } else {
    newMessageFile.value = null;
  }
};

const clearFileInput = () => {
  newMessageFile.value = null;
  fileInputKey.value++;
};

const handleSendMessage = async () => {
  if (!newMessageText.value.trim() && !newMessageFile.value) {
    localError.value = "Message text or attachment is required.";
    return;
  }
  if (!activeConversation.value) {
    localError.value = "No active conversation selected.";
    return;
  }

  localError.value = null;

  let messageType: "TEXT" | "AUDIO" | "VOICE" = "TEXT";
  if (newMessageFile.value) {
    if (newMessageFile.value.type.startsWith("audio/")) {
      messageType = "AUDIO";
    } else {
      if (!newMessageText.value.trim()) {
        localError.value =
          "Non-audio attachments are not supported without text. Please provide text or an audio file.";
        return;
      }
    }
  }

  const success = await chatStore.sendReply(conversationId.value, {
    text: newMessageText.value.trim() || null,
    attachment: newMessageFile.value,
    message_type: messageType,
  });

  if (success) {
    newMessageText.value = "";
    clearFileInput();
    scrollToBottom(true);
  } else {
    localError.value = chatStore.error || "Failed to send message.";
  }
};

const handleAcceptRequest = async () => {
  if (!activeConversation.value) return;
  localError.value = null;
  const success = await chatStore.acceptChatRequest(
    activeConversation.value.id
  );
  if (!success) {
    localError.value = chatStore.error || "Failed to accept DM request.";
  } else {
    // Optionally, re-fetch messages or update UI to show it's accepted
    // The conversation object in the store is updated, so computed properties should react.
  }
};

const conversationPartnerName = computed(() => {
  if (!activeConversation.value || !authStore.authUser) return "Conversation";
  if (activeConversation.value.related_artist) {
    if (activeConversation.value.initiator?.id === authStore.authUser.id) {
      return activeConversation.value.related_artist.name + " (Artist)";
    } else {
      const otherUser = activeConversation.value.participants.find(
        (p) => p.id !== authStore.authUser?.id
      );
      return otherUser
        ? otherUser.username
        : activeConversation.value.related_artist.name + " (Artist)";
    }
  } else {
    const otherUser = activeConversation.value.participants.find(
      (p) => p.id !== authStore.authUser?.id
    );
    return otherUser ? otherUser.username : "User";
  }
});
</script>

<template>
  <div class="chat-conversation-view">
    <div class="chat-header">
      <button @click="router.push({ name: 'chat-list' })" class="back-button">
        ← Back to Chats
      </button>
      <h3>{{ conversationPartnerName }}</h3>
      <div
        v-if="activeConversation?.related_artist"
        class="artist-context-badge"
      >
        Artist DM
      </div>
    </div>

    <div
      v-if="
        localError &&
        !chatStore.isLoadingMessages &&
        !chatStore.isLoadingConversations
      "
      class="error-message global-error"
    >
      {{ localError }}
    </div>

    <div v-if="showAcceptButton" class="accept-request-banner">
      <p>This is a new direct message request.</p>
      <button
        @click="handleAcceptRequest"
        :disabled="chatStore.isSendingMessage"
      >
        Accept Chat
      </button>
    </div>

    <div class="messages-container" ref="messageContainerRef">
      <div
        v-if="
          chatStore.isLoadingMessages ||
          (chatStore.isLoadingConversations && !activeConversation)
        "
        class="loading"
      >
        Loading messages...
      </div>
      <div
        v-else-if="
          chatStore.activeConversationMessages.length === 0 &&
          !localError &&
          activeConversation
        "
        class="empty-chat"
      >
        <p v-if="activeConversation?.is_accepted">
          No messages yet. Start the conversation!
        </p>
        <p
          v-else-if="
            activeConversation?.initiator?.id === authStore.authUser?.id
          "
        >
          Your message request has been sent.
        </p>
        <p v-else>Accept the request to start chatting.</p>
      </div>
      <ChatMessageItem
        v-for="message in chatStore.activeConversationMessages"
        :key="message.id"
        :message="message"
      />
    </div>

    <div class="message-input-area" v-if="canInteract && activeConversation">
      <textarea
        v-model="newMessageText"
        placeholder="Type your message..."
        rows="2"
        @keyup.enter.exact="handleSendMessage"
        :disabled="chatStore.isSendingMessage"
      ></textarea>
      <div class="file-input-controls">
        <label
          for="file-upload"
          class="file-upload-button"
          :class="{ disabled: chatStore.isSendingMessage }"
        >
          📎 Attach Audio
        </label>
        <input
          type="file"
          id="file-upload"
          :key="fileInputKey"
          @change="handleFileChange"
          accept="audio/*"
          :disabled="chatStore.isSendingMessage"
        />
        <span v-if="newMessageFile" class="file-name-display">
          {{ newMessageFile.name }}
          <button
            @click="clearFileInput"
            class="clear-file-btn"
            :disabled="chatStore.isSendingMessage"
            title="Remove file"
          >
            ×
          </button>
        </span>
      </div>
      <button
        @click="handleSendMessage"
        :disabled="chatStore.isSendingMessage"
        class="send-button"
      >
        {{ chatStore.isSendingMessage ? "Sending..." : "Send" }}
      </button>
    </div>
    <div
      v-else-if="
        activeConversation &&
        !activeConversation.is_accepted &&
        activeConversation.initiator?.id === authStore.authUser?.id
      "
      class="info-banner"
    >
      Waiting for {{ conversationPartnerName }} to accept your message request.
    </div>
    <div
      v-else-if="activeConversation && !canInteract && !showAcceptButton"
      class="info-banner"
    >
      You cannot send messages to this conversation currently.
    </div>
  </div>
</template>

<style scoped>
.chat-conversation-view {
  display: flex;
  flex-direction: column;
  height: calc(
    100vh - 120px
  ); /* Adjust based on your header/footer/player height */
  max-width: 800px;
  margin: 0 auto;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--color-background-soft);
}

.chat-header {
  padding: 0.75rem 1rem;
  background-color: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  gap: 1rem;
}
.chat-header h3 {
  margin: 0;
  flex-grow: 1;
  font-size: 1.2em;
}
.back-button {
  background: none;
  border: none;
  font-size: 1em;
  cursor: pointer;
  color: var(--color-link);
  padding: 0.2em 0.5em;
}
.back-button:hover {
  text-decoration: underline;
}
.artist-context-badge {
  font-size: 0.8em;
  padding: 0.2em 0.5em;
  border-radius: 4px;
  background-color: var(--color-accent);
  color: var(--vt-c-white);
}

.accept-request-banner {
  padding: 0.75rem 1rem;
  background-color: var(--color-accent-soft, #e6f7ff);
  border-bottom: 1px solid var(--color-accent);
  text-align: center;
}
.accept-request-banner p {
  margin: 0 0 0.5rem 0;
  font-size: 0.9em;
}
.accept-request-banner button {
  padding: 0.4em 0.8em;
}

.messages-container {
  flex-grow: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.loading,
.empty-chat {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-light);
  font-style: italic;
  margin: auto; /* Center it vertically too */
}
.empty-chat p {
  margin-bottom: 0.5rem;
}

.message-input-area {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-border);
  background-color: var(--color-background-mute);
  display: flex;
  align-items: flex-end;
  gap: 0.75rem;
}
.message-input-area textarea {
  flex-grow: 1;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  resize: none;
  font-size: 1em;
  line-height: 1.4;
  max-height: 100px;
  overflow-y: auto;
}
.message-input-area textarea:disabled {
  background-color: var(--color-background-soft);
}

.file-input-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.3rem;
}

.file-upload-button {
  padding: 0.5em 0.8em;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
}
.file-upload-button:hover {
  border-color: var(--color-border-hover);
}
.file-upload-button.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

input[type="file"] {
  display: none;
}
.file-name-display {
  font-size: 0.8em;
  color: var(--color-text-light);
  display: flex;
  align-items: center;
  gap: 0.3em;
}
.clear-file-btn {
  background: none;
  border: none;
  color: var(--vt-c-red-dark);
  font-size: 1.2em;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.clear-file-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.send-button {
  padding: 0.6rem 1rem;
  font-size: 1em;
  min-height: calc(0.6rem * 2 + 1.4em);
}
.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.info-banner {
  padding: 0.75rem 1rem;
  background-color: var(--color-background-mute);
  text-align: center;
  font-style: italic;
  color: var(--color-text-light);
  font-size: 0.9em;
}
.global-error {
  padding: 0.5rem 1rem;
  font-size: 0.9em;
  text-align: center;
  background-color: var(--vt-c-red-soft);
  color: var(--vt-c-red-dark);
  border-bottom: 1px solid var(--vt-c-red-dark);
}
</style>
