<script setup lang="ts">
import type { ChatMessage } from "@/types";
import { computed } from "vue";
import { useAuthStore } from "@/stores/auth";

const props = defineProps<{
  message: ChatMessage;
}>();

const authStore = useAuthStore();

const isMyMessage = computed(() => {
  return props.message.sender.id === authStore.authUser?.id;
});

const formattedTimestamp = computed(() => {
  return new Date(props.message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
});
</script>

<template>
  <div
    class="chat-message-item"
    :class="{ 'my-message': isMyMessage, 'their-message': !isMyMessage }"
  >
    <div class="message-bubble">
      <div v-if="!isMyMessage" class="sender-name">
        {{ message.sender.username }}
      </div>
      <div
        v-if="message.message_type === 'TEXT' && message.text"
        class="message-text"
      >
        {{ message.text }}
      </div>
      <div
        v-else-if="
          message.message_type === 'AUDIO' || message.message_type === 'VOICE'
        "
        class="message-attachment"
      >
        <audio
          v-if="message.attachment_url"
          controls
          :src="message.attachment_url"
        >
          Your browser does not support the audio element.
        </audio>
        <p v-else>[Audio attachment processing or unavailable]</p>
        <a
          v-if="message.attachment_url"
          :href="message.attachment_url"
          target="_blank"
          download
          class="download-link"
          >Download Audio</a
        >
      </div>
      <!-- TODO: Handle TRACK_SHARE type -->
      <div class="message-timestamp">{{ formattedTimestamp }}</div>
    </div>
  </div>
</template>

<style scoped>
.chat-message-item {
  display: flex;
  margin-bottom: 0.5rem;
}
.my-message {
  justify-content: flex-end;
}
.their-message {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 0.6rem 0.9rem;
  border-radius: 12px;
  line-height: 1.4;
  word-wrap: break-word;
}
.my-message .message-bubble {
  background-color: var(--color-accent);
  color: white;
  border-bottom-right-radius: 4px;
}
.their-message .message-bubble {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border-bottom-left-radius: 4px;
  border: 1px solid var(--color-border);
}

.sender-name {
  font-size: 0.8em;
  font-weight: bold;
  margin-bottom: 0.2rem;
  color: var(--color-text-light); /* For their messages */
}
.my-message .sender-name {
  display: none; /* Don't show own name */
}

.message-text {
  white-space: pre-wrap; /* Preserve line breaks */
}
.message-attachment audio {
  max-width: 100%;
  border-radius: 6px;
  margin-bottom: 0.3rem;
}
.download-link {
  font-size: 0.8em;
  margin-top: 0.3rem;
  display: inline-block;
  color: var(--color-link);
}
.my-message .download-link {
  color: #e0e0ff; /* Lighter link for dark bubble */
}
.download-link:hover {
  text-decoration: underline;
}

.message-timestamp {
  font-size: 0.75em;
  margin-top: 0.3rem;
  text-align: right;
}
.my-message .message-timestamp {
  color: rgba(255, 255, 255, 0.7);
}
.their-message .message-timestamp {
  color: var(--color-text-light);
}
</style>
