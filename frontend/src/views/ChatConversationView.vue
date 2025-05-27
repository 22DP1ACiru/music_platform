<script setup lang="ts">
import { ref, onMounted, watch, nextTick, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChatStore } from "@/stores/chat";
import { useAuthStore } from "@/stores/auth";
import type { ChatMessage, Conversation, ReplyMessagePayload } from "@/types"; // Use ReplyMessagePayload
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
const MAX_MESSAGE_LENGTH = 1000;

// REMOVED: selectedReplyIdentity ref, as it's no longer needed for replies

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

const remainingChars = computed(() => {
  return MAX_MESSAGE_LENGTH - newMessageText.value.length;
});

const canInteract = computed(() => {
  if (!activeConversation.value) return false;
  return (
    activeConversation.value.is_accepted ||
    (authStore.authUser &&
      activeConversation.value.initiator_user?.id !== authStore.authUser.id) // Check against initiator_user
  );
});

const showAcceptButton = computed(() => {
  return (
    activeConversation.value &&
    !activeConversation.value.is_accepted &&
    authStore.authUser &&
    activeConversation.value.initiator_user?.id !== authStore.authUser.id // Check against initiator_user
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

  if (
    chatStore.conversations.length === 0 &&
    authStore.isLoggedIn &&
    !chatStore.isLoadingConversations
  ) {
    await chatStore.fetchConversations();
  }

  if (!activeConversation.value) {
    if (!chatStore.error) {
      localError.value = "Conversation not found or you do not have access.";
    } else {
      localError.value = chatStore.error;
    }
    chatStore.clearActiveConversation();
    return;
  }

  await chatStore.fetchMessagesForConversation(conversationId.value);
  if (chatStore.error && !localError.value) {
    localError.value = chatStore.error;
  }
  scrollToBottom();
};

onMounted(() => {
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
  if (newMessageText.value.length > MAX_MESSAGE_LENGTH) {
    localError.value = `Message cannot exceed ${MAX_MESSAGE_LENGTH} characters.`;
    return;
  }
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

  // Use ReplyMessagePayload - identity fields are NOT sent for replies
  const payload: ReplyMessagePayload = {
    text: newMessageText.value.trim() || null,
    attachment: newMessageFile.value,
    message_type: messageType,
  };

  const success = await chatStore.sendReply(conversationId.value, payload);

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
  }
};

const conversationPartnerName = computed(() => {
  if (!activeConversation.value || !authStore.authUser) return "Conversation";

  const conv = activeConversation.value;
  const currentUser = authStore.authUser;

  // Case 1: Conversation is TO an artist profile
  if (conv.related_artist_recipient_details) {
    // If the current user is NOT the owner of this artist profile, then the partner is the artist.
    if (
      conv.related_artist_recipient_details.id !== authStore.artistProfileId
    ) {
      return `${conv.related_artist_recipient_details.name} [Artist]`;
    }
    // If the current user IS the owner of this artist profile, the partner is the initiator.
    // Display the initiator's identity.
    if (conv.initiator_user) {
      if (
        conv.initiator_identity_type === "ARTIST" &&
        conv.initiator_artist_profile_details
      ) {
        return `${conv.initiator_artist_profile_details.name} [Artist]`;
      }
      return `${conv.initiator_user.username} [User]`;
    }
  } else {
    // Case 2: Standard User-to-User DM (no artist recipient)
    // Find the other participant who is not the current user.
    const otherParticipant = conv.participants.find(
      (p) => p.id !== currentUser.id
    );
    if (otherParticipant) {
      // Check how the other user (who is the initiator in this simple 2-party context if not me) initiated.
      // This assumes in a 2-party non-artist-recipient DM, the other person is the initiator if I am not.
      if (conv.initiator_user?.id === otherParticipant.id) {
        if (
          conv.initiator_identity_type === "ARTIST" &&
          conv.initiator_artist_profile_details
        ) {
          return `${conv.initiator_artist_profile_details.name} [Artist]`;
        }
        return `${otherParticipant.username} [User]`;
      }
      return `${otherParticipant.username} [User]`; // Fallback
    }
  }
  return "User"; // Fallback
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
        v-if="activeConversation?.related_artist_recipient_details"
        class="artist-context-badge"
      >
        Artist DM Context
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
            activeConversation?.initiator_user?.id === authStore.authUser?.id
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
      <div class="input-controls-wrapper">
        <div class="textarea-wrapper">
          <textarea
            v-model="newMessageText"
            placeholder="Type your message..."
            rows="2"
            @keyup.enter.exact="
              !chatStore.isSendingMessage &&
                remainingChars >= 0 &&
                handleSendMessage()
            "
            :disabled="chatStore.isSendingMessage"
            :maxlength="MAX_MESSAGE_LENGTH"
          ></textarea>
          <div
            class="char-counter"
            :class="{ 'limit-exceeded': remainingChars < 0 }"
          >
            {{ remainingChars }}
          </div>
        </div>
        <div class="actions-row">
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
          <!-- REMOVED Identity Selector for replies -->
          <!-- 
            <div v-if="authStore.hasArtistProfile" class="identity-selector">
                <label for="reply-identity">Send as:</label>
                <select id="reply-identity" v-model="selectedReplyIdentity" :disabled="chatStore.isSendingMessage">
                    <option value="USER">{{ authStore.authUser?.username }} (User)</option>
                    <option value="ARTIST">{{ authStore.authUser?.profile?.artist_profile_data?.name }} (Artist)</option>
                </select>
            </div>
             -->
        </div>
      </div>
      <button
        @click="handleSendMessage"
        :disabled="chatStore.isSendingMessage || remainingChars < 0"
        class="send-button"
      >
        {{ chatStore.isSendingMessage ? "Sending..." : "Send" }}
      </button>
    </div>
    <div
      v-else-if="
        activeConversation &&
        !activeConversation.is_accepted &&
        activeConversation.initiator_user?.id === authStore.authUser?.id
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
  height: calc(100vh - 120px);
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
  margin: auto;
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

.input-controls-wrapper {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.textarea-wrapper {
  flex-grow: 1;
  position: relative;
  width: 100%;
}

.message-input-area textarea {
  width: 100%;
  padding: 0.6rem;
  padding-bottom: 1.8em;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  resize: none;
  font-size: 1em;
  line-height: 1.4;
  max-height: 100px;
  overflow-y: auto;
  box-sizing: border-box;
}
.message-input-area textarea:disabled {
  background-color: var(--color-background-soft);
}
.char-counter {
  position: absolute;
  bottom: 5px;
  right: 8px;
  font-size: 0.75em;
  color: var(--color-text-light);
}
.char-counter.limit-exceeded {
  color: var(--vt-c-red-dark);
  font-weight: bold;
}

.actions-row {
  display: flex;
  justify-content: space-between; /* This will push file input left and identity selector (if present) right */
  align-items: center;
  width: 100%;
}

.file-input-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Removed .identity-selector styles as it's removed from this component */

.file-upload-button {
  padding: 0.5em 0.8em;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  white-space: nowrap;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
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
  align-self: flex-end;
  height: fit-content;
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
