<script setup lang="ts">
import type { Conversation, ChatMessage } from "@/types";
import { computed } from "vue";
import { useAuthStore } from "@/stores/auth";

const props = defineProps<{
  conversation: Conversation;
}>();

const authStore = useAuthStore();

// Helper to get display name for a message's sender
const getMessageSenderDisplay = (message: ChatMessage | null): string => {
  if (!message) return "";
  if (
    message.sender_identity_type === "ARTIST" &&
    message.sending_artist_details
  ) {
    return message.sending_artist_details.name; // For snippet, just artist name is fine
  }
  return message.sender_user.username;
};

// Determines who the conversation is "with" from the current user's perspective
const displayParticipant = computed(() => {
  if (!authStore.authUser || !props.conversation.participants.length)
    return "Conversation";

  const conv = props.conversation;
  const currentUser = authStore.authUser;

  // Find the other User model among participants
  const otherUserModel = conv.participants.find((p) => p.id !== currentUser.id);

  // Case 1: Conversation is directed TO an artist profile (related_artist_recipient is set)
  if (conv.related_artist_recipient_details) {
    // If the current user is the owner of this target artist profile (i.e., DM is TO ME as Artist)
    if (
      authStore.artistProfileId &&
      conv.related_artist_recipient_details.id === authStore.artistProfileId
    ) {
      // The "other party" is the initiator of the conversation. Display their initiating identity.
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
      // The DM is to an artist, and I am not that artist (i.e., I am DMing an Artist)
      // The "other party" is the target artist.
      return `${conv.related_artist_recipient_details.name} [Artist]`;
    }
  }
  // Case 2: Standard User-to-User DM (related_artist_recipient is null)
  // OR an Artist initiated a DM to me (as a User).
  else if (otherUserModel) {
    // otherUserModel must exist in a 2-party DM
    // If the other user is the initiator and they initiated as an Artist
    if (
      conv.initiator_user?.id === otherUserModel.id &&
      conv.initiator_identity_type === "ARTIST" &&
      conv.initiator_artist_profile_details
    ) {
      return `${conv.initiator_artist_profile_details.name} [Artist]`;
    }
    // Otherwise, it's the other user (as a User)
    return `${otherUserModel.username} [User]`;
  }

  return "Unknown Contact"; // Fallback
});

const lastMessageSnippet = computed(() => {
  const msg = props.conversation.latest_message;
  if (!msg) return "No messages yet.";

  let prefix = "";
  // Check if the sender_user of the last message is the current authenticated user
  if (msg.sender_user.id === authStore.authUser?.id) {
    prefix = "You: ";
  } else {
    // Optional: If you want to show who sent the last message in the snippet when it's not you.
    // This might make the snippet too long. Consider if needed.
    // const senderName = getMessageSenderDisplay(msg);
    // prefix = senderName ? `${senderName}: ` : "";
  }

  let snippetContent = "";
  if (msg.message_type === "AUDIO" || msg.message_type === "VOICE") {
    snippetContent = `Sent an audio file`; // More descriptive than just [Audio File]
    if (msg.original_attachment_filename) {
      snippetContent = `Audio: ${msg.original_attachment_filename}`;
    }
  } else if (msg.message_type === "TRACK_SHARE") {
    snippetContent = "[Shared Track]"; // Placeholder
  } else {
    snippetContent = msg.text || "[Attachment without text]";
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
    : new Date(props.conversation.updated_at); // Fallback to conversation update if no message

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
  return props.conversation.unread_count > 0 && props.conversation.is_accepted;
});

const avatarDisplay = computed(() => {
  if (!authStore.authUser) return { type: "initials", value: "?" };

  const conv = props.conversation;
  const currentUser = authStore.authUser;

  // If DM is to an artist, and I am NOT that artist. Avatar is the target artist.
  if (
    conv.related_artist_recipient_details &&
    conv.related_artist_recipient_details.id !== authStore.artistProfileId
  ) {
    return {
      type: "image",
      value: conv.related_artist_recipient_details.artist_picture,
      alt: conv.related_artist_recipient_details.name,
    };
  }

  // If DM is to MY artist profile. Avatar is the initiator.
  if (
    conv.related_artist_recipient_details &&
    conv.related_artist_recipient_details.id === authStore.artistProfileId
  ) {
    if (
      conv.initiator_identity_type === "ARTIST" &&
      conv.initiator_artist_profile_details
    ) {
      return {
        type: "image",
        value: conv.initiator_artist_profile_details.artist_picture,
        alt: conv.initiator_artist_profile_details.name,
      };
    } else if (conv.initiator_user) {
      // Later: fetch UserProfile picture for conv.initiator_user.id
      return {
        type: "initials",
        value: conv.initiator_user.username.charAt(0).toUpperCase(),
      };
    }
  }

  // Standard User-to-User DM, or Artist initiated to me (as User). Avatar is the other party.
  const otherUserModel = conv.participants.find((p) => p.id !== currentUser.id);
  if (otherUserModel) {
    // If this other user is the initiator and initiated as Artist
    if (
      conv.initiator_user?.id === otherUserModel.id &&
      conv.initiator_identity_type === "ARTIST" &&
      conv.initiator_artist_profile_details
    ) {
      return {
        type: "image",
        value: conv.initiator_artist_profile_details.artist_picture,
        alt: conv.initiator_artist_profile_details.name,
      };
    }
    // Otherwise, it's the other user (as User)
    // Later: fetch UserProfile picture for otherUserModel.id
    return {
      type: "initials",
      value: otherUserModel.username.charAt(0).toUpperCase(),
    };
  }

  return { type: "initials", value: "?" }; // Fallback
});
</script>

<template>
  <div
    class="conversation-list-item"
    :class="{ unread: isUnread, pending: !conversation.is_accepted }"
  >
    <div class="avatar-placeholder">
      <img
        v-if="avatarDisplay.type === 'image' && avatarDisplay.value"
        :src="avatarDisplay.value"
        :alt="avatarDisplay.alt || 'Avatar'"
        class="avatar-img"
      />
      <div
        v-else-if="avatarDisplay.type === 'initials'"
        class="avatar-initials"
      >
        {{ avatarDisplay.value }}
      </div>
      <div v-else class="avatar-initials">?</div>
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
    <div v-if="isUnread" class="unread-indicator">
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
  /* Last message boldness handled by snippet now */
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
  /* Add boldness for unread last messages */
  font-weight: bold;
  color: var(--color-text); /* Make it darker for unread */
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
