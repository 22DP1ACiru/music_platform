<script setup lang="ts">
import type { Conversation, ChatMessage, UserChatInfo } from "@/types"; // Added UserChatInfo
import { computed } from "vue";
import { useAuthStore } from "@/stores/auth";

const props = defineProps<{
  conversation: Conversation;
}>();

const authStore = useAuthStore();

// Display name is now directly from conversation.other_participant_display_name
const displayParticipantName = computed(() => {
  return props.conversation.other_participant_display_name || "Conversation";
});

const lastMessageSnippet = computed(() => {
  const msg = props.conversation.latest_message;
  if (!msg) return "No messages yet.";

  let prefix = "";
  if (msg.sender_user.id === authStore.authUser?.id) {
    prefix = "You: ";
  }

  let snippetContent = "";
  if (msg.message_type === "AUDIO" || msg.message_type === "VOICE") {
    snippetContent = msg.original_attachment_filename
      ? `Audio: ${msg.original_attachment_filename}`
      : `Sent an audio file`;
  } else if (msg.message_type === "TRACK_SHARE") {
    snippetContent = "[Shared Track]";
  } else {
    snippetContent = msg.text || "[Attachment]";
  }

  const fullSnippet = prefix + snippetContent;
  const maxLength = 45;
  return fullSnippet.length > maxLength
    ? fullSnippet.substring(0, maxLength - 3) + "..."
    : fullSnippet;
});

const formattedTimestamp = computed(() => {
  const dateToFormat = props.conversation.latest_message
    ? new Date(props.conversation.latest_message.timestamp)
    : new Date(props.conversation.updated_at);

  const today = new Date();
  if (dateToFormat.toDateString() === today.toDateString()) {
    return dateToFormat.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  return dateToFormat.toLocaleDateString();
});

const isUnread = computed(() => {
  // Only show unread count if conversation is accepted OR if it's a request TO ME
  return (
    props.conversation.unread_count > 0 &&
    (props.conversation.is_accepted ||
      props.conversation.initiator_user?.id !== authStore.authUser?.id)
  );
});

// Determines the avatar to display for the "other party" in the conversation.
const avatarDetails = computed(() => {
  const conv = props.conversation;
  const currentUser = authStore.authUser;
  if (!currentUser) return { type: "initials", value: "?", alt: "Unknown" };

  let otherPartyUser: UserChatInfo | null = null;
  let otherPartyArtist: {
    id: number;
    name: string;
    artist_picture: string | null;
  } | null = null;

  // Scenario 1: Conversation is directed TO an artist profile
  if (conv.related_artist_recipient_details) {
    // If I am the owner of this target artist profile (DM is TO MY artist)
    if (
      authStore.artistProfileId &&
      conv.related_artist_recipient_details.id === authStore.artistProfileId
    ) {
      // The "other party" is the initiator.
      if (
        conv.initiator_identity_type === "ARTIST" &&
        conv.initiator_artist_profile_details
      ) {
        otherPartyArtist = conv.initiator_artist_profile_details;
      } else if (conv.initiator_user) {
        otherPartyUser = conv.initiator_user;
      }
    } else {
      // I am not the owner of the target artist (e.g., I DMed them).
      // The "other party" is the target artist.
      otherPartyArtist = conv.related_artist_recipient_details;
    }
  }
  // Scenario 2: User-to-User DM context (no specific artist recipient)
  else {
    const otherParticipantModel = conv.participants.find(
      (p) => p.id !== currentUser.id
    );
    if (otherParticipantModel) {
      // If this other participant is the initiator AND they initiated as an Artist
      if (
        conv.initiator_user?.id === otherParticipantModel.id &&
        conv.initiator_identity_type === "ARTIST" &&
        conv.initiator_artist_profile_details
      ) {
        otherPartyArtist = conv.initiator_artist_profile_details;
      } else {
        // Standard User-to-User, or an Artist DMed me (as User), display the User.
        otherPartyUser = otherParticipantModel;
      }
    }
  }

  // Determine avatar based on resolved other party
  if (otherPartyArtist && otherPartyArtist.artist_picture) {
    return {
      type: "image",
      value: otherPartyArtist.artist_picture,
      alt: otherPartyArtist.name,
    };
  } else if (otherPartyArtist) {
    // Artist without picture, use initials of artist name
    return {
      type: "initials",
      value: otherPartyArtist.name.charAt(0).toUpperCase(),
      alt: otherPartyArtist.name,
    };
  } else if (otherPartyUser) {
    // User (potentially with profile picture in UserChatInfo if extended)
    // For now, use initials of username
    return {
      type: "initials",
      value: otherPartyUser.username.charAt(0).toUpperCase(),
      alt: otherPartyUser.username,
    };
  }

  return { type: "initials", value: "?", alt: "Unknown" }; // Fallback
});
</script>

<template>
  <div
    class="conversation-list-item"
    :class="{ unread: isUnread, pending: !conversation.is_accepted }"
  >
    <div class="avatar-placeholder">
      <img
        v-if="avatarDetails.type === 'image' && avatarDetails.value"
        :src="avatarDetails.value"
        :alt="avatarDetails.alt"
        class="avatar-img"
      />
      <div
        v-else-if="avatarDetails.type === 'initials'"
        class="avatar-initials"
      >
        {{ avatarDetails.value }}
      </div>
      <div v-else class="avatar-initials">?</div>
    </div>
    <div class="conversation-info">
      <div class="info-header">
        <span class="participant-name">{{ displayParticipantName }}</span>
        <span class="timestamp">{{ formattedTimestamp }}</span>
      </div>
      <div class="last-message">
        <span
          v-if="
            !conversation.is_accepted &&
            conversation.initiator_user?.id !== authStore.authUser?.id
          "
          class="request-badge"
        >
          DM Request
        </span>
        <span
          v-else-if="
            !conversation.is_accepted &&
            conversation.initiator_user?.id === authStore.authUser?.id
          "
          class="request-badge-sent"
        >
          Request Sent
        </span>
        <span v-else>{{ lastMessageSnippet }}</span>
      </div>
    </div>
    <div
      v-if="isUnread && conversation.unread_count > 0"
      class="unread-indicator"
    >
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
.conversation-list-item.unread .participant-name {
  font-weight: bold;
}
.conversation-list-item.pending {
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
  overflow: hidden;
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
.conversation-list-item.unread .last-message {
  font-weight: bold;
  color: var(--color-text);
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
