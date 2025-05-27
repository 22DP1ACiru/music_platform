<script setup lang="ts">
import type { Conversation } from "@/types";
import { computed } from "vue";
import { useAuthStore } from "@/stores/auth";

const props = defineProps<{
  conversation: Conversation;
}>();

const authStore = useAuthStore();

const displayParticipant = computed(() => {
  if (!authStore.authUser) return "Loading...";

  if (props.conversation.related_artist) {
    // It's an artist context conversation
    if (props.conversation.initiator?.id === authStore.authUser.id) {
      // Current user initiated it to an artist
      return props.conversation.related_artist.name + " (Artist)";
    } else {
      // Current user (as artist owner) received it from another user
      // Find the other user who is not the artist's owner
      const otherUser = props.conversation.participants.find(
        (p) => p.id !== authStore.authUser?.id
      );
      return otherUser
        ? otherUser.username
        : props.conversation.related_artist.name + " (Artist)";
    }
  } else {
    // It's a direct user-to-user DM
    const otherUser = props.conversation.participants.find(
      (p) => p.id !== authStore.authUser?.id
    );
    return otherUser ? otherUser.username : "Unknown User";
  }
});

const lastMessageSnippet = computed(() => {
  const msg = props.conversation.latest_message;
  if (!msg) return "No messages yet.";
  let snippet = "";
  if (msg.sender.id === authStore.authUser?.id) {
    snippet += "You: ";
  }
  if (msg.message_type === "AUDIO" || msg.message_type === "VOICE") {
    snippet += "[Audio File]";
  } else if (msg.message_type === "TRACK_SHARE") {
    snippet += "[Shared Track]";
  } else {
    snippet += msg.text || "[Attachment]";
  }
  return snippet.length > 50 ? snippet.substring(0, 47) + "..." : snippet;
});

const formattedTimestamp = computed(() => {
  if (!props.conversation.latest_message)
    return new Date(props.conversation.updated_at).toLocaleDateString();
  const date = new Date(props.conversation.latest_message.timestamp);
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return date.toLocaleDateString();
});

const isUnread = computed(() => {
  return props.conversation.unread_count > 0;
});
</script>

<template>
  <div
    class="conversation-list-item"
    :class="{ unread: isUnread, pending: !conversation.is_accepted }"
  >
    <div class="avatar-placeholder">
      <!-- TODO: Add user/artist avatar here -->
      <img
        v-if="conversation.related_artist?.artist_picture"
        :src="conversation.related_artist.artist_picture"
        alt="Artist Avatar"
        class="avatar-img"
      />
      <!-- Add logic for user avatars if available -->
      <div v-else class="avatar-initials">
        {{ displayParticipant?.charAt(0).toUpperCase() }}
      </div>
    </div>
    <div class="conversation-info">
      <div class="info-header">
        <span class="participant-name">{{ displayParticipant }}</span>
        <span class="timestamp">{{ formattedTimestamp }}</span>
      </div>
      <div class="last-message">
        <span
          v-if="
            !conversation.is_accepted &&
            conversation.initiator?.id !== authStore.authUser?.id
          "
          class="request-badge"
        >
          DM Request
        </span>
        <span
          v-else-if="
            !conversation.is_accepted &&
            conversation.initiator?.id === authStore.authUser?.id
          "
          class="request-badge-sent"
        >
          Request Sent
        </span>
        <span v-else>{{ lastMessageSnippet }}</span>
      </div>
    </div>
    <div v-if="isUnread && conversation.is_accepted" class="unread-indicator">
      {{ conversation.unread_count }}
    </div>
  </div>
</template>

<style scoped>
.conversation-list-item {
  display: flex;
  align-items: center;
  padding: 0.8rem 0.5rem;
  border-bottom: 1px solid var(--color-border-hover);
  cursor: pointer;
  transition: background-color 0.2s ease;
}
.conversation-list-item:hover {
  background-color: var(--color-background-mute);
}
.conversation-list-item.unread .participant-name,
.conversation-list-item.unread .last-message {
  font-weight: bold;
}
.conversation-list-item.pending {
  /* Optional: slightly different style for pending requests */
  opacity: 0.85;
}

.avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 1rem;
  flex-shrink: 0;
  overflow: hidden; /* For images */
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-initials {
  font-size: 1.2em;
  color: var(--color-background-soft);
  font-weight: bold;
}

.conversation-info {
  flex-grow: 1;
  overflow: hidden;
}
.info-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.2rem;
}
.participant-name {
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.timestamp {
  font-size: 0.75em;
  color: var(--color-text-light);
  flex-shrink: 0;
  margin-left: 0.5rem;
}
.last-message {
  font-size: 0.9em;
  color: var(--color-text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.request-badge,
.request-badge-sent {
  font-style: italic;
  padding: 0.1em 0.4em;
  border-radius: 3px;
  font-size: 0.8em;
}
.request-badge {
  background-color: var(--color-accent);
  color: var(--vt-c-white);
}
.request-badge-sent {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.unread-indicator {
  background-color: var(--color-accent);
  color: white;
  font-size: 0.75em;
  font-weight: bold;
  padding: 0.2em 0.5em;
  border-radius: 10px;
  margin-left: 0.5rem;
  min-width: 18px;
  text-align: center;
}
</style>
