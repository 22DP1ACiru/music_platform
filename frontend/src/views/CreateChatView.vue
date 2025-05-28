<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import type { CreateMessagePayload } from "@/types";
import axios from "axios"; // For fetching users/artists if needed

const authStore = useAuthStore();
const chatStore = useChatStore();
const router = useRouter();

interface SelectableUser {
  id: number;
  username: string;
}
interface SelectableArtist {
  id: number;
  name: string;
  user_id: number; // Owner's user ID
}

const recipientType = ref<"user" | "artist">("user");
const selectedUserId = ref<number | null>(null);
const selectedArtistId = ref<number | null>(null);
const messageText = ref("");
const attachmentFile = ref<File | null>(null);
const messageType = ref<"TEXT" | "AUDIO" | "VOICE">("TEXT"); // Default to TEXT

// For selecting the identity to send AS
const sendAsIdentity = ref<"USER" | "ARTIST">(
  authStore.hasArtistProfile ? "ARTIST" : "USER"
); // Default to artist if available

const availableUsers = ref<SelectableUser[]>([]);
const availableArtists = ref<SelectableArtist[]>([]);

const isLoadingRecipients = ref(false);
const isSending = ref(false);
const errorMessage = ref<string | null>(null);

const fetchUsers = async () => {
  // Simplified: In a real app, you'd have pagination/search
  // and exclude the current user
  try {
    const response = await axios.get("/users/"); // Assuming a /users/ endpoint lists users
    availableUsers.value = response.data.results.filter(
      (u: any) => u.id !== authStore.authUser?.id
    );
  } catch (error) {
    console.error("Failed to fetch users:", error);
  }
};

const fetchArtists = async () => {
  // Simplified: In a real app, you'd have pagination/search
  // and potentially exclude the user's own artist profile if sending as USER
  try {
    const response = await axios.get("/artists/"); // Assuming /artists/ lists artists
    availableArtists.value = response.data.results.filter(
      (a: SelectableArtist) => {
        // Don't list own artist profile if sending as USER to avoid User X -> Artist X
        if (
          sendAsIdentity.value === "USER" &&
          a.user_id === authStore.authUser?.id
        ) {
          return false;
        }
        // Don't list own artist profile if sending as ARTIST to avoid Artist X -> Artist X
        if (
          sendAsIdentity.value === "ARTIST" &&
          a.id === authStore.artistProfileId
        ) {
          return false;
        }
        return true;
      }
    );
  } catch (error) {
    console.error("Failed to fetch artists:", error);
  }
};

onMounted(async () => {
  isLoadingRecipients.value = true;
  await fetchUsers();
  await fetchArtists();
  isLoadingRecipients.value = false;
  if (!authStore.hasArtistProfile) {
    sendAsIdentity.value = "USER";
  }
});

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    attachmentFile.value = target.files[0];
    // Auto-set message type if an audio file is selected (optional UX)
    if (attachmentFile.value.type.startsWith("audio/")) {
      messageType.value = "AUDIO"; // Or VOICE depending on your distinction
    }
  } else {
    attachmentFile.value = null;
  }
};

const handleSubmit = async () => {
  if (
    (recipientType.value === "user" && !selectedUserId.value) ||
    (recipientType.value === "artist" && !selectedArtistId.value)
  ) {
    errorMessage.value = "Please select a recipient.";
    return;
  }
  if (!messageText.value && !attachmentFile.value) {
    errorMessage.value = "Please enter a message or add an attachment.";
    return;
  }

  isSending.value = true;
  errorMessage.value = null;

  const payload: CreateMessagePayload = {
    text: messageText.value || null,
    attachment: attachmentFile.value || undefined, // Send undefined if null to omit from FormData
    message_type: attachmentFile.value ? messageType.value : "TEXT",
    initiator_identity_type: sendAsIdentity.value,
  };

  if (recipientType.value === "user") {
    payload.recipient_user_id = selectedUserId.value;
  } else {
    payload.recipient_artist_id = selectedArtistId.value;
  }

  if (sendAsIdentity.value === "ARTIST" && authStore.artistProfileId) {
    payload.initiator_artist_profile_id = authStore.artistProfileId;
  }

  const newConversation = await chatStore.sendInitialMessage(payload);
  isSending.value = false;

  if (newConversation) {
    router.push({
      name: "chat-conversation",
      params: { conversationId: newConversation.id.toString() },
    });
  } else {
    errorMessage.value =
      chatStore.error || "Failed to send message. Please try again.";
  }
};
</script>

<template>
  <div class="create-chat-view">
    <h2>Start a New Conversation</h2>
    <form @submit.prevent="handleSubmit" class="new-message-form">
      <div class="form-group" v-if="authStore.hasArtistProfile">
        <label>Send as:</label>
        <div class="identity-switch">
          <button
            type="button"
            @click="sendAsIdentity = 'USER'"
            :class="{ active: sendAsIdentity === 'USER' }"
          >
            {{ authStore.authUser?.username }} [User]
          </button>
          <button
            type="button"
            @click="sendAsIdentity = 'ARTIST'"
            :class="{ active: sendAsIdentity === 'ARTIST' }"
            v-if="authStore.artistProfileId"
          >
            <!-- You'll need to fetch artist name if not in authStore -->
            My Artist Profile [Artist]
          </button>
        </div>
      </div>

      <div class="form-group">
        <label>Recipient Type:</label>
        <select v-model="recipientType">
          <option value="user">User</option>
          <option value="artist">Artist</option>
        </select>
      </div>

      <div class="form-group" v-if="recipientType === 'user'">
        <label for="recipient-user">Select User:</label>
        <select id="recipient-user" v-model="selectedUserId">
          <option :value="null" disabled>-- Select a user --</option>
          <option
            v-for="user in availableUsers"
            :key="user.id"
            :value="user.id"
          >
            {{ user.username }}
          </option>
        </select>
      </div>

      <div class="form-group" v-if="recipientType === 'artist'">
        <label for="recipient-artist">Select Artist:</label>
        <select id="recipient-artist" v-model="selectedArtistId">
          <option :value="null" disabled>-- Select an artist --</option>
          <option
            v-for="artist in availableArtists"
            :key="artist.id"
            :value="artist.id"
          >
            {{ artist.name }}
          </option>
        </select>
      </div>
      <div v-if="isLoadingRecipients">Loading recipients...</div>

      <div class="form-group">
        <label for="message-text">Message:</label>
        <textarea
          id="message-text"
          v-model="messageText"
          rows="4"
          placeholder="Type your message..."
        ></textarea>
      </div>

      <div class="form-group">
        <label for="message-attachment">Attach Audio/Voice (Optional):</label>
        <input
          type="file"
          id="message-attachment"
          @change="handleFileChange"
          accept="audio/*"
        />
        <select
          v-if="attachmentFile"
          v-model="messageType"
          class="message-type-select"
        >
          <option value="AUDIO">Audio Attachment</option>
          <option value="VOICE">Voice Message</option>
        </select>
      </div>

      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <div class="form-actions">
        <button type="submit" :disabled="isSending">
          {{ isSending ? "Sending..." : "Send Message" }}
        </button>
        <button type="button" @click="router.go(-1)" :disabled="isSending">
          Cancel
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.create-chat-view {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background-color: var(--color-background-soft);
}
.create-chat-view h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}
.new-message-form .form-group {
  margin-bottom: 1rem;
}
.new-message-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}
.new-message-form input[type="file"],
.new-message-form select,
.new-message-form textarea {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1em;
}
.new-message-form textarea {
  resize: vertical;
  min-height: 80px;
}
.identity-switch {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.identity-switch button {
  flex-grow: 1;
  padding: 0.5em;
  border: 1px solid var(--color-border);
  background-color: var(--color-background-mute);
  cursor: pointer;
}
.identity-switch button.active {
  background-color: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}
.message-type-select {
  margin-top: 0.5rem;
}
.form-actions {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}
.form-actions button[type="button"] {
  background-color: var(--color-background-mute);
  border-color: var(--color-border);
  color: var(--color-text);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red);
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
}
</style>
