<script setup lang="ts">
import type { ChatMessage } from "@/types";
import { computed, ref, watch, onMounted, onUnmounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import axios from "axios";

const props = defineProps<{
  message: ChatMessage;
}>();

const authStore = useAuthStore();
const audioSrc = ref<string | null>(null);
const isLoadingAudio = ref(false);
const audioError = ref<string | null>(null);
const isDownloading = ref(false); // New state for download button
let objectUrlPlayback: string | null = null;

const isMyMessage = computed(() => {
  return props.message.sender.id === authStore.authUser?.id;
});

const formattedTimestamp = computed(() => {
  return new Date(props.message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
});

const displayFilename = computed(() => {
  if (props.message.original_attachment_filename) {
    const name = props.message.original_attachment_filename;
    const maxLength = 30;
    if (name.length > maxLength) {
      const extMatch = name.match(/\.[0-9a-z]+$/i);
      const ext = extMatch ? extMatch[0] : "";
      const nameWithoutExt = name.substring(0, name.length - ext.length);
      return (
        nameWithoutExt.substring(0, maxLength - 3 - ext.length) + "..." + ext
      );
    }
    return name;
  }
  return "attachment";
});

// This URL is for the API endpoint, not directly for href
const baseAttachmentApiUrl = computed(() => {
  return props.message.attachment_url; // This is already /api/chat/messages/<id>/download/
});

const downloadAttributeFilename = computed(() => {
  return props.message.original_attachment_filename || "download";
});

const fetchAudioAsBlob = async (url: string): Promise<Blob | null> => {
  try {
    const response = await axios.get(url, {
      responseType: "blob",
    });
    return response.data;
  } catch (error) {
    console.error("Failed to fetch audio blob from URL:", url, error);
    return null;
  }
};

const fetchAudioForPlayback = async () => {
  if (!baseAttachmentApiUrl.value || props.message.message_type === "TEXT") {
    audioSrc.value = null;
    return;
  }
  if (audioSrc.value || isLoadingAudio.value) return;

  isLoadingAudio.value = true;
  audioError.value = null;
  const blob = await fetchAudioAsBlob(baseAttachmentApiUrl.value); // No query param needed for playback
  if (blob) {
    if (objectUrlPlayback) {
      URL.revokeObjectURL(objectUrlPlayback);
    }
    objectUrlPlayback = URL.createObjectURL(blob);
    audioSrc.value = objectUrlPlayback;
  } else {
    audioError.value = "Could not load audio for playback.";
    audioSrc.value = null;
  }
  isLoadingAudio.value = false;
};

const handleDownloadAttachment = async () => {
  if (!baseAttachmentApiUrl.value || isDownloading.value) return;

  isDownloading.value = true;
  audioError.value = null; // Clear previous errors

  // Construct the URL that tells the backend to force download
  const downloadUrlWithParam = `${baseAttachmentApiUrl.value}${
    baseAttachmentApiUrl.value.includes("?") ? "&" : "?"
  }download=true`;

  const blob = await fetchAudioAsBlob(downloadUrlWithParam);
  if (blob) {
    const link = document.createElement("a");
    const objectUrlDownload = URL.createObjectURL(blob);
    link.href = objectUrlDownload;
    link.setAttribute("download", downloadAttributeFilename.value);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(objectUrlDownload); // Clean up the download object URL
  } else {
    audioError.value = "Could not download the attachment.";
  }
  isDownloading.value = false;
};

watch(
  () => props.message.attachment_url,
  (newUrl) => {
    if (
      newUrl &&
      (props.message.message_type === "AUDIO" ||
        props.message.message_type === "VOICE")
    ) {
      fetchAudioForPlayback();
    } else {
      if (objectUrlPlayback) {
        URL.revokeObjectURL(objectUrlPlayback);
        objectUrlPlayback = null;
      }
      audioSrc.value = null;
    }
  },
  { immediate: true }
);

onMounted(() => {
  if (
    props.message.attachment_url &&
    (props.message.message_type === "AUDIO" ||
      props.message.message_type === "VOICE")
  ) {
    fetchAudioForPlayback();
  }
});

onUnmounted(() => {
  if (objectUrlPlayback) {
    URL.revokeObjectURL(objectUrlPlayback);
  }
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

      <div v-if="message.text" class="message-text">
        {{ message.text }}
      </div>

      <div
        v-if="
          message.message_type === 'AUDIO' || message.message_type === 'VOICE'
        "
        class="message-attachment audio-attachment"
      >
        <div class="attachment-filename" v-if="message.attachment_url">
          {{ displayFilename }}
        </div>

        <div v-if="isLoadingAudio" class="loading-audio">Loading audio...</div>
        <div v-else-if="audioError && !audioSrc" class="audio-error">
          {{ audioError }}
        </div>
        <!-- Show general audio error if src is also null -->
        <audio
          v-else-if="audioSrc"
          controls
          :src="audioSrc"
          controlslist="nodownload noremoteplayback"
        >
          Your browser does not support the audio element.
        </audio>
        <p v-else-if="!message.attachment_url">
          [Audio attachment processing or unavailable]
        </p>

        <!-- Use a button to trigger JS download -->
        <button
          v-if="message.attachment_url"
          @click="handleDownloadAttachment"
          class="download-button"
          :disabled="isDownloading"
        >
          {{ isDownloading ? "Downloading..." : "Download Audio" }}
        </button>
        <div
          v-if="audioError && isDownloading"
          class="audio-error download-error-inline"
        >
          {{ audioError }}
        </div>
      </div>
      <div
        v-else-if="message.attachment_url && message.message_type !== 'TEXT'"
        class="message-attachment generic-attachment"
      >
        <div class="attachment-filename">{{ displayFilename }}</div>
        <button
          @click="handleDownloadAttachment"
          class="download-button"
          :disabled="isDownloading"
        >
          {{ isDownloading ? "Downloading..." : "Download Attachment" }}
        </button>
        <div
          v-if="audioError && isDownloading"
          class="audio-error download-error-inline"
        >
          {{ audioError }}
        </div>
      </div>

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
  display: flex;
  flex-direction: column;
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
  color: var(--color-text-light);
}
.my-message .sender-name {
  display: none;
}

.message-text {
  white-space: pre-wrap;
  margin-bottom: 0.3rem;
}
.message-attachment {
  margin-top: 0.3rem;
}
.loading-audio,
.audio-error {
  font-style: italic;
  font-size: 0.9em;
  color: var(--color-text-light);
  padding: 0.5em 0;
}
.audio-error {
  color: var(--vt-c-red-dark);
}
.download-error-inline {
  font-size: 0.8em;
  margin-top: 0.2em;
}
.message-attachment.audio-attachment audio {
  max-width: 100%;
  min-width: 250px;
  border-radius: 6px;
  margin-bottom: 0.3rem;
}
.attachment-filename {
  font-size: 0.85em;
  color: var(--color-text-light);
  margin-bottom: 0.25rem;
  font-style: italic;
  word-break: break-all;
}
.my-message .attachment-filename {
  color: rgba(255, 255, 255, 0.8);
}

/* Changed from <a> to <button> */
.download-button {
  font-size: 0.8em;
  margin-top: 0.3rem;
  display: inline-block;
  color: var(--color-link);
  background: none;
  border: none;
  padding: 0.2em 0.4em;
  cursor: pointer;
  text-decoration: underline;
}
.my-message .download-button {
  color: #e0e0ff;
}
.download-button:hover:not(:disabled) {
  color: var(--color-link-hover);
}
.download-button:disabled {
  color: var(--color-text-light);
  cursor: not-allowed;
  text-decoration: none;
}

.message-timestamp {
  font-size: 0.75em;
  margin-top: 0.3rem;
  text-align: right;
  align-self: flex-end;
}
.my-message .message-timestamp {
  color: rgba(255, 255, 255, 0.7);
}
.their-message .message-timestamp {
  color: var(--color-text-light);
}
</style>
