<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChatStore } from "@/stores/chat";
import { useAuthStore } from "@/stores/auth";
import ChatMessageItem from "@/components/chat/ChatMessageItem.vue";
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

const conversationId = ref<number | null>(null);
const messages = computed(() => chatStore.activeConversationMessages);
const isLoading = computed(
  () => chatStore.isLoadingMessages || chatStore.isSendingMessage
);
const error = computed(() => chatStore.error);

const newMessageText = ref("");
const newMessageFile = ref<File | null>(null);
const messageType = ref<"TEXT" | "AUDIO" | "VOICE">("TEXT");

const messageListRef = ref<HTMLElement | null>(null);

// For Compose Mode
const isComposeMode = ref(false);
const recipientInfo = ref<{
  type: "USER" | "ARTIST";
  id: number;
  name: string; // Username or Artist Name
  senderIdentity: "USER" | "ARTIST"; // How the current user is sending
  senderArtistProfileId?: number | null; // If senderIdentity is ARTIST
} | null>(null);

const activeConversation = computed<Conversation | undefined>(() => {
  if (conversationId.value) {
    return chatStore.conversations.find((c) => c.id === conversationId.value);
  }
  return undefined;
});

const displayRecipientName = computed(() => {
  if (isComposeMode.value && recipientInfo.value) {
    return `New message to: ${recipientInfo.value.name} [${recipientInfo.value.type}]`;
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

  chatStore.clearActiveConversation(); // Clear previous active state

  if (cIdParam && !isNaN(parseInt(cIdParam))) {
    isComposeMode.value = false;
    recipientInfo.value = null;
    conversationId.value = parseInt(cIdParam);
    await chatStore.fetchMessagesForConversation(conversationId.value);
    scrollToBottom();
  } else if (queryRecipientUserId || queryRecipientArtistId) {
    isComposeMode.value = true;
    conversationId.value = null; // No existing conversation ID yet

    let type: "USER" | "ARTIST" = "USER";
    let id: number = 0;
    let name: string = "Unknown"; // Placeholder

    if (queryRecipientUserId) {
      type = "USER";
      id = parseInt(queryRecipientUserId);
      // Ideally, fetch user details here to get username if not easily available
      // For now, we might not have the name immediately.
      // A better approach: chatStore could have a function to fetch user/artist chat info.
      name = `User ID ${id}`; // Temporary
    } else if (queryRecipientArtistId) {
      type = "ARTIST";
      id = parseInt(queryRecipientArtistId);
      name = `Artist ID ${id}`; // Temporary
    }

    // Determine sender identity for the new message
    const senderIdentity =
      querySenderIdentity || chatStore.currentChatViewIdentity;
    let senderArtistProfileId: number | null = null;
    if (senderIdentity === "ARTIST") {
      senderArtistProfileId = querySenderArtistProfileId
        ? parseInt(querySenderArtistProfileId)
        : authStore.artistProfileId;
    }

    // Attempt to fetch recipient name (simple implementation)
    try {
      if (type === "USER") {
        const userRes = await axios.get<{ username: string }>(`/users/${id}/`);
        name = userRes.data.username;
      } else if (type === "ARTIST") {
        const artistRes = await axios.get<{ name: string }>(`/artists/${id}/`);
        name = artistRes.data.name;
      }
    } catch (e) {
      console.warn("Could not fetch recipient name for compose mode:", e);
    }

    recipientInfo.value = {
      type,
      id,
      name,
      senderIdentity,
      senderArtistProfileId,
    };
    chatStore.activeConversationMessages.value = []; // Clear messages for compose mode
  } else {
    // Invalid state, redirect or show error
    router.push({ name: "chat-list" });
  }
}

const handleSendMessage = async () => {
  if (!newMessageText.value.trim() && !newMessageFile.value) {
    alert("Message cannot be empty.");
    return;
  }

  if (isComposeMode.value && recipientInfo.value) {
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
      // Successfully created, switch out of compose mode and load this conversation
      isComposeMode.value = false;
      recipientInfo.value = null;
      // Critical: update route to reflect the new conversation ID to avoid re-composing on refresh
      await router.replace({
        name: "chat-conversation",
        params: { conversationId: newConversation.id.toString() },
        query: {},
      });
      // `loadConversationOrPrepareCompose` will be triggered by watcher or needs manual call
      // conversationId.value = newConversation.id;
      // await chatStore.fetchMessagesForConversation(newConversation.id); // Already handled by store/route watcher
    }
  } else if (conversationId.value) {
    await chatStore.sendReply(conversationId.value, {
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
  if (fileInput) fileInput.value = ""; // Reset file input
  scrollToBottom();
};

const handleAcceptRequest = async () => {
  if (conversationId.value) {
    const success = await chatStore.acceptChatRequest(conversationId.value);
    if (success) {
      // Optionally show a success message or rely on UI update
    } else {
      alert("Failed to accept chat request: " + chatStore.error);
    }
  }
};

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    newMessageFile.value = target.files[0];
    // Basic type detection for message_type, can be more sophisticated
    if (newMessageFile.value.type.startsWith("audio/")) {
      messageType.value = "AUDIO"; // Or VOICE, needs distinction
    } else {
      messageType.value = "TEXT"; // Fallback if attachment is not audio but still sent with text
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
  () => route.fullPath, // Watch fullPath to react to query param changes for compose mode too
  () => {
    loadConversationOrPrepareCompose();
  },
  { immediate: false } // `onMounted` handles initial load
);

watch(
  messages,
  () => {
    scrollToBottom();
  },
  { deep: true }
);

watch(
  () => chatStore.activeConversationId,
  (newId, oldId) => {
    if (newId !== oldId) {
      // If activeConversationId changes in the store (e.g. by WebSocket update),
      // ensure this view reacts if it's relevant.
      // This is mostly handled by the route watcher though.
    }
  }
);

// Go back to chat list
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
      <!-- Spacer for alignment -->
    </div>

    <div v-if="canAcceptRequest" class="accept-request-banner">
      <p>This is a message request. Accept to start chatting.</p>
      <button @click="handleAcceptRequest" :disabled="isLoading">
        Accept Request
      </button>
    </div>

    <div v-if="isLoading && messages.length === 0" class="loading-messages">
      Loading messages...
    </div>
    <div v-else-if="error && messages.length === 0" class="error-messages">
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
      <div v-if="isComposeMode && messages.length === 0" class="no-messages">
        Start the conversation by sending a message.
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
      <span v-if="newMessageFile" class="selected-file-name">{{
        newMessageFile.name
      }}</span>

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
  margin-right: 0.5rem; /* Space for file input */
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
  display: none; /* Hide the actual file input */
}
.file-input-label {
  padding: 0.5rem;
  font-size: 1.5rem; /* Adjust icon size */
  cursor: pointer;
  color: var(--color-text-light);
  margin-right: 0.5rem;
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
  max-width: 150px; /* Adjust as needed */
}
</style>
