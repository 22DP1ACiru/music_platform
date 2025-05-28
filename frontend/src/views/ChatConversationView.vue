<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChatStore } from "@/stores/chat";
import { useAuthStore } from "@/stores/auth";
import ChatMessageItem from "@/components/chat/ChatMessageItem.vue";
import axios from "axios";
import type {
  ChatMessage,
  Conversation,
  UserChatInfo,
  ArtistChatInfo,
  CreateMessagePayload,
} from "@/types";

const route = useRoute();
const router = useRouter();
const chatStore = useChatStore();
const authStore = useAuthStore();

const conversationIdInternal = ref<number | null>(null);
const messages = computed(() => chatStore.activeConversationMessages);
const isLoading = computed(
  () => chatStore.isLoadingMessages || chatStore.isSendingMessage
);
const error = computed(() => chatStore.error);

const newMessageText = ref("");
const newMessageFile = ref<File | null>(null);
const messageType = ref<"TEXT" | "AUDIO" | "VOICE">("TEXT");

const messageListRef = ref<HTMLElement | null>(null);

const isComposeMode = ref(false);
const recipientInfo = ref<{
  type: "USER" | "ARTIST";
  id: number;
  name: string;
  senderIdentity: "USER" | "ARTIST";
  senderArtistProfileId?: number | null;
} | null>(null);

const activeConversation = computed<Conversation | undefined>(() => {
  if (conversationIdInternal.value) {
    return chatStore.conversations.find(
      (c) => c.id === conversationIdInternal.value
    );
  }
  return undefined;
});

const displayRecipientName = computed(() => {
  if (isComposeMode.value && recipientInfo.value) {
    return `New message to: ${
      recipientInfo.value.name
    } [${recipientInfo.value.type.toUpperCase()}]`;
  }
  if (activeConversation.value) {
    return (
      activeConversation.value.other_participant_display_name || "Conversation"
    );
  }
  return "Chat";
});

const canAcceptRequest = computed(() => {
  return (
    activeConversation.value &&
    !activeConversation.value.is_accepted &&
    activeConversation.value.initiator_user?.id !== authStore.authUser?.id
  );
});

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

async function loadConversationOrPrepareCompose() {
  const cIdParam = route.params.conversationId as string;
  const queryRecipientUserId = route.query.recipientUserId as string;
  const queryRecipientArtistId = route.query.recipientArtistId as string;
  const querySenderIdentity = route.query.senderIdentity as "USER" | "ARTIST";
  const querySenderArtistProfileId = route.query
    .senderArtistProfileId as string;

  chatStore.clearActiveConversation();
  recipientInfo.value = null; // Reset recipient info

  if (cIdParam && cIdParam !== "new" && !isNaN(parseInt(cIdParam))) {
    isComposeMode.value = false;
    conversationIdInternal.value = parseInt(cIdParam);
    await chatStore.fetchMessagesForConversation(conversationIdInternal.value);
    scrollToBottom();
  } else if (
    cIdParam === "new" &&
    (queryRecipientUserId || queryRecipientArtistId)
  ) {
    isComposeMode.value = true;
    conversationIdInternal.value = null;

    let type: "USER" | "ARTIST" = "USER";
    let id: number = 0;
    // Initialize recipientInfo with a loading state for the name

    if (queryRecipientUserId) {
      type = "USER";
      id = parseInt(queryRecipientUserId);
    } else if (queryRecipientArtistId) {
      type = "ARTIST";
      id = parseInt(queryRecipientArtistId);
    }

    const senderIdentity =
      querySenderIdentity || chatStore.currentChatViewIdentity;
    let senderArtistProfileId: number | null = null;
    if (senderIdentity === "ARTIST") {
      senderArtistProfileId = querySenderArtistProfileId
        ? parseInt(querySenderArtistProfileId)
        : authStore.artistProfileId;
    }

    // Set recipientInfo with a placeholder/loading name first
    recipientInfo.value = {
      type,
      id,
      name: `Loading ${type.toLowerCase()} info...`,
      senderIdentity,
      senderArtistProfileId,
    };
    chatStore.activeConversationMessages.value = [];

    // Then fetch the actual name
    try {
      let fetchedName = "Unknown";
      if (type === "USER" && id) {
        const userRes = await axios.get<{ username: string }>(`/users/${id}/`);
        fetchedName = userRes.data.username;
      } else if (type === "ARTIST" && id) {
        const artistRes = await axios.get<{ name: string }>(`/artists/${id}/`);
        fetchedName = artistRes.data.name;
      }
      // Update the name property of the reactive recipientInfo object
      if (recipientInfo.value) {
        // Check if recipientInfo is still relevant (user hasn't navigated away)
        recipientInfo.value.name = fetchedName;
      }
    } catch (e) {
      console.warn("Could not fetch recipient name for compose mode:", e);
      if (recipientInfo.value) {
        recipientInfo.value.name = `Error loading ${type.toLowerCase()} info`;
      }
      error.value = "Could not load recipient details. Please try again.";
    }
  } else {
    console.warn(
      "ChatConversationView: Invalid route state. Params:",
      route.params,
      "Query:",
      route.query
    );
    router.push({ name: "chat-list" });
  }
}

const handleSendMessage = async () => {
  if (!newMessageText.value.trim() && !newMessageFile.value) {
    alert("Message cannot be empty.");
    return;
  }

  if (isComposeMode.value && recipientInfo.value) {
    // Ensure recipient ID is valid before sending
    if (!recipientInfo.value.id || recipientInfo.value.id === 0) {
      alert("Recipient information is incomplete. Cannot send message.");
      console.error(
        "Attempted to send message with invalid recipient ID:",
        recipientInfo.value.id
      );
      return;
    }

    const payload: CreateMessagePayload = {
      text: newMessageText.value,
      attachment: newMessageFile.value || undefined,
      message_type: newMessageFile.value ? messageType.value : "TEXT",
      initiator_identity_type: recipientInfo.value.senderIdentity,
      initiator_artist_profile_id: recipientInfo.value.senderArtistProfileId,
    };
    if (recipientInfo.value.type === "USER") {
      payload.recipient_user_id = recipientInfo.value.id;
    } else {
      payload.recipient_artist_id = recipientInfo.value.id;
    }

    const newConversation = await chatStore.sendInitialMessage(payload);
    if (newConversation) {
      isComposeMode.value = false;
      // recipientInfo.value = null; // Keep recipientInfo for a moment if needed for UI transition
      await router.replace({
        name: "chat-conversation",
        params: { conversationId: newConversation.id.toString() },
        query: {},
      });
      // Watcher on route.fullPath will trigger loadConversationOrPrepareCompose
    }
  } else if (conversationIdInternal.value) {
    await chatStore.sendReply(conversationIdInternal.value, {
      text: newMessageText.value,
      attachment: newMessageFile.value || undefined,
      message_type: newMessageFile.value ? messageType.value : "TEXT",
    });
  }

  newMessageText.value = "";
  newMessageFile.value = null;
  const fileInput = document.getElementById(
    "message-file-input"
  ) as HTMLInputElement;
  if (fileInput) fileInput.value = "";
  scrollToBottom();
};

const handleAcceptRequest = async () => {
  if (conversationIdInternal.value) {
    const success = await chatStore.acceptChatRequest(
      conversationIdInternal.value
    );
    if (success) {
      // UI should update
    } else {
      alert("Failed to accept chat request: " + chatStore.error);
    }
  }
};

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    newMessageFile.value = target.files[0];
    if (newMessageFile.value.type.startsWith("audio/")) {
      messageType.value = "AUDIO";
    } else {
      // For any other file type, if text is also present, it's fine.
      // If no text, and it's not audio, it's a generic attachment.
      // Backend validation handles if text is required based on type.
      // For now, let's simplify: if attachment exists, type depends on its nature.
      // The backend `CreateMessageSerializer` seems to validate text based on message_type,
      // which is fine. The default `message_type` on the payload will be TEXT if only text is provided.
      // If an attachment is provided, we set a more specific type here.
      // If it's not audio, and we want to support other attachments,
      // we'd need more types (e.g., 'IMAGE', 'FILE').
      // For now, non-audio with attachment but no text might default to message_type TEXT by payload,
      // which backend might reject if it's only an attachment.
      // The `sendInitialMessage` and `sendReply` set message_type based on `newMessageFile.value`.
      messageType.value = "TEXT"; // Default if not audio, can be overridden by user choice if UI supports it
    }
  } else {
    newMessageFile.value = null;
    messageType.value = "TEXT";
  }
};

onMounted(() => {
  loadConversationOrPrepareCompose();
});

watch(
  () => route.fullPath,
  (newPath, oldPath) => {
    if (newPath !== oldPath) {
      // Only reload if the full path actually changed
      loadConversationOrPrepareCompose();
    }
  },
  { immediate: false }
);

watch(
  messages,
  () => {
    scrollToBottom();
  },
  { deep: true }
);

const goBack = () => {
  chatStore.clearActiveConversation();
  router.push({ name: "chat-list" });
};
</script>

<template>
  <div class="chat-conversation-view">
    <div class="conversation-header">
      <button @click="goBack" class="back-button">< Back</button>
      <h3>{{ displayRecipientName }}</h3>
      <div class="header-spacer"></div>
    </div>

    <div v-if="canAcceptRequest" class="accept-request-banner">
      <p>This is a message request. Accept to start chatting.</p>
      <button @click="handleAcceptRequest" :disabled="isLoading">
        Accept Request
      </button>
    </div>

    <div
      v-if="isLoading && messages.length === 0 && !isComposeMode"
      class="loading-messages"
    >
      Loading messages...
    </div>
    <div v-if="isLoading && isComposeMode" class="loading-messages">
      Preparing chat...
    </div>
    <div
      v-else-if="error && messages.length === 0 && !isComposeMode"
      class="error-messages"
    >
      {{ error }}
    </div>

    <div class="message-list" ref="messageListRef">
      <ChatMessageItem
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
      <div
        v-if="messages.length === 0 && !isComposeMode && !isLoading && !error"
        class="no-messages"
      >
        No messages in this conversation yet.
      </div>
      <div
        v-if="isComposeMode && messages.length === 0 && !error && !isLoading"
        class="no-messages"
      >
        Start the conversation by sending a message.
      </div>
      <div v-if="isComposeMode && error" class="error-messages">
        {{ error }}
      </div>
    </div>

    <form @submit.prevent="handleSendMessage" class="message-input-form">
      <input
        type="file"
        @change="handleFileChange"
        id="message-file-input"
        class="file-input"
        title="Attach file"
      />
      <label for="message-file-input" class="file-input-label">📎</label>
      <span
        v-if="newMessageFile"
        class="selected-file-name"
        :title="newMessageFile.name"
        >{{ newMessageFile.name }}</span
      >

      <textarea
        v-model="newMessageText"
        placeholder="Type your message..."
        @keyup.enter.exact.prevent="handleSendMessage"
        :disabled="
          isLoading ||
          (activeConversation &&
            !activeConversation.is_accepted &&
            !isComposeMode &&
            !canAcceptRequest)
        "
      ></textarea>
      <button
        type="submit"
        :disabled="
          isLoading ||
          (activeConversation &&
            !activeConversation.is_accepted &&
            !isComposeMode &&
            !canAcceptRequest)
        "
      >
        Send
      </button>
    </form>
  </div>
</template>

<style scoped>
.chat-conversation-view {
  display: flex;
  flex-direction: column;
  height: calc(
    100vh - 60px - 70px - 4rem
  ); /* Adjust based on Navbar and Player heights and padding */
  max-width: 800px;
  margin: 1rem auto;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.conversation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1rem;
  background-color: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
}
.conversation-header h3 {
  margin: 0;
  font-size: 1.2em;
  color: var(--color-heading);
  text-align: center;
  flex-grow: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.back-button {
  background: none;
  border: none;
  font-size: 1em;
  color: var(--color-link);
  cursor: pointer;
  padding: 0.3em 0.5em;
}
.header-spacer {
  min-width: 60px; /* Approx width of back button */
}

.accept-request-banner {
  padding: 0.8rem 1rem;
  background-color: var(
    --color-accent-soft,
    #e6f7ff
  ); /* Define this color in base.css if needed */
  color: var(--color-accent-dark, #005f8d); /* Define this */
  text-align: center;
  border-bottom: 1px solid var(--color-accent);
}
.accept-request-banner p {
  margin: 0 0 0.5rem 0;
  font-size: 0.9em;
}
.accept-request-banner button {
  padding: 0.3em 0.8em;
  font-size: 0.9em;
  background-color: var(--color-accent);
  color: white;
  border: none;
  border-radius: 4px;
}

.message-list {
  flex-grow: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}
.loading-messages,
.error-messages,
.no-messages {
  text-align: center;
  margin-top: 2rem;
  color: var(--color-text-light);
  font-style: italic;
}
.error-messages {
  color: var(--vt-c-red);
}

.message-input-form {
  display: flex;
  padding: 0.8rem 1rem;
  border-top: 1px solid var(--color-border);
  background-color: var(--color-background-soft);
  align-items: center; /* Align items vertically */
}
.message-input-form textarea {
  flex-grow: 1;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  resize: none;
  min-height: 40px; /* Initial height */
  max-height: 120px; /* Max height before scroll */
  line-height: 1.4;
  font-size: 1em;
  margin-right: 0.5rem;
  margin-left: 0.5rem;
}
.message-input-form button[type="submit"] {
  padding: 0.6rem 1rem;
  background-color: var(--color-accent);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
.message-input-form button:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}

.file-input {
  display: none;
}
.file-input-label {
  padding: 0.5rem;
  font-size: 1.5rem;
  cursor: pointer;
  color: var(--color-text-light);
}
.file-input-label:hover {
  color: var(--color-accent);
}
.selected-file-name {
  font-size: 0.8em;
  color: var(--color-text-light);
  margin-right: 0.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100px; /* Shorter max-width for selected file name */
  display: inline-block; /* Ensure ellipsis works */
  vertical-align: middle; /* Align with textarea */
}
</style>
