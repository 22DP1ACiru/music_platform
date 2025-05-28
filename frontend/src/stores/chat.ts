import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import { useAuthStore } from "./auth";
import type {
  Conversation,
  ChatMessage,
  CreateMessagePayload,
  ReplyMessagePayload,
} from "@/types";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ChatViewIdentityType = "USER" | "ARTIST";

export const useChatStore = defineStore("chat", () => {
  const authStore = useAuthStore();

  const conversations = ref<Conversation[]>([]);
  const activeConversationMessages = ref<ChatMessage[]>([]);
  const activeConversationId = ref<number | null>(null);

  const isLoadingConversations = ref(false);
  const isLoadingMessages = ref(false);
  const isSendingMessage = ref(false);
  const error = ref<string | null>(null);

  // New state for current viewing identity
  const currentChatViewIdentity = ref<ChatViewIdentityType>("USER");
  // Assuming a user can only have one artist profile for now.
  // If multiple, this would need to be the ID of the selected artist profile.
  const activeArtistProfileIdForChat = computed(
    () => authStore.artistProfileId
  );

  function setActiveChatViewIdentity(identity: ChatViewIdentityType) {
    if (identity === "ARTIST" && !authStore.hasArtistProfile) {
      currentChatViewIdentity.value = "USER"; // Fallback if no artist profile
    } else {
      currentChatViewIdentity.value = identity;
    }
    // When identity changes, clear active conversation as it might not be relevant
    clearActiveConversation();
  }

  const displayedConversations = computed(() => {
    if (!authStore.authUser) return [];
    const currentUserId = authStore.authUser.id;

    if (currentChatViewIdentity.value === "USER") {
      return conversations.value.filter((conv) => {
        // 1. I initiated as USER
        if (
          conv.initiator_user?.id === currentUserId &&
          conv.initiator_identity_type === "USER"
        ) {
          return true;
        }
        // 2. I am a participant (not initiator), and it's a User-to-User DM to me, or Artist-to-User DM to me.
        //    Essentially, any conversation where I am a participant and the conversation is not *specifically* directed to one of my artist profiles.
        //    AND my role in this conversation, from my perspective, is "USER".
        //    A conversation is considered a "User" chat for me if:
        //    - I initiated it as "USER".
        //    - It's a DM to me as "USER" (i.e., `related_artist_recipient_details` is null and I am a participant but not initiator, OR
        //      `related_artist_recipient_details` is not *my* artist profile).
        const iAmInitiator = conv.initiator_user?.id === currentUserId;
        const iAmParticipant = conv.participants.some(
          (p) => p.id === currentUserId
        );

        if (!iAmParticipant) return false; // I must be in the conversation

        if (iAmInitiator) {
          // I started it
          return conv.initiator_identity_type === "USER";
        } else {
          // Someone else started it, I am a recipient
          // If it's directed TO an artist, it's not for my USER persona unless that artist ISN'T MINE.
          // This case is tricky. Simpler: if it's NOT directed to MY artist profile, it can be a user chat for me.
          if (conv.related_artist_recipient_details) {
            // It's to an artist. Is it *my* artist?
            if (
              activeArtistProfileIdForChat.value &&
              conv.related_artist_recipient_details.id ===
                activeArtistProfileIdForChat.value
            ) {
              return false; // This is for my artist persona, not user.
            } else {
              // It's to *someone else's* artist, and I (as user) am somehow a participant.
              // This scenario is less common unless group chats are involved or backend logic is complex.
              // For strict User DMs, this means it must be purely User-to-User or Artist-to-User (where I am the user).
              // If `conv.related_artist_recipient_details` is present but NOT mine, and I'm a non-initiator participant,
              // it's effectively not a direct DM to my USER persona.
              return false;
            }
          } else {
            // Not directed to any artist, so it's a User-to-User or Artist-to-User (to me)
            return true;
          }
        }
      });
    } else if (currentChatViewIdentity.value === "ARTIST") {
      if (!activeArtistProfileIdForChat.value) return [];
      const myArtistId = activeArtistProfileIdForChat.value;
      return conversations.value.filter((conv) => {
        // 1. I initiated as THIS ARTIST
        if (
          conv.initiator_user?.id === currentUserId &&
          conv.initiator_identity_type === "ARTIST" &&
          conv.initiator_artist_profile_details?.id === myArtistId
        ) {
          return true;
        }
        // 2. Conversation is directed TO THIS ARTIST profile
        if (conv.related_artist_recipient_details?.id === myArtistId) {
          return true;
        }
        return false;
      });
    }
    return []; // Should not happen
  });

  async function fetchConversations() {
    if (!authStore.isLoggedIn) return;
    isLoadingConversations.value = true;
    error.value = null;
    try {
      const response = await axios.get<PaginatedResponse<Conversation>>(
        "/chat/conversations/"
      );
      conversations.value = response.data.results.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
    } catch (err) {
      console.error("Chat Store: Failed to fetch conversations:", err);
      error.value = "Could not load conversations.";
      conversations.value = [];
    } finally {
      isLoadingConversations.value = false;
    }
  }

  async function fetchMessagesForConversation(conversationId: number) {
    if (!authStore.isLoggedIn) return;
    activeConversationId.value = conversationId;
    isLoadingMessages.value = true;
    error.value = null;
    try {
      const response = await axios.get<PaginatedResponse<ChatMessage>>(
        `/chat/conversations/${conversationId}/messages/`
      );
      activeConversationMessages.value = response.data.results;
      const conversation = conversations.value.find(
        (c) => c.id === conversationId
      );
      if (conversation) {
        // Mark messages as read on the frontend immediately for unread count
        // Backend's `list_messages` view handles marking them read in DB.
        const unreadMessagesFromOthers =
          activeConversationMessages.value.filter(
            (msg) =>
              !msg.is_read && msg.sender_user.id !== authStore.authUser?.id
          ).length;
        if (unreadMessagesFromOthers > 0) {
          conversation.unread_count = Math.max(
            0,
            conversation.unread_count - unreadMessagesFromOthers
          );
        }
        // If the conversation was a request to me and I'm opening it, mark it accepted on frontend
        if (
          !conversation.is_accepted &&
          conversation.initiator_user?.id !== authStore.authUser?.id
        ) {
          // conversation.is_accepted = true; // This should be confirmed by acceptChatRequest
        }
      }
    } catch (err) {
      console.error(
        `Chat Store: Failed to fetch messages for conv ${conversationId}:`,
        err
      );
      error.value = "Could not load messages.";
      activeConversationMessages.value = [];
    } finally {
      isLoadingMessages.value = false;
    }
  }

  async function sendInitialMessage(
    payload: CreateMessagePayload
  ): Promise<Conversation | null> {
    if (!authStore.isLoggedIn) {
      error.value = "You must be logged in to send messages.";
      return null;
    }
    isSendingMessage.value = true;
    error.value = null;
    const formData = new FormData();

    if (payload.recipient_user_id) {
      formData.append("recipient_user_id", String(payload.recipient_user_id));
    }
    if (payload.recipient_artist_id) {
      formData.append(
        "recipient_artist_id",
        String(payload.recipient_artist_id)
      );
    }
    if (payload.text) formData.append("text", payload.text);
    if (payload.attachment) formData.append("attachment", payload.attachment);
    formData.append("message_type", payload.message_type || "TEXT");

    // Determine initiator identity based on current view or payload
    const effectiveInitiatorIdentity =
      payload.initiator_identity_type || currentChatViewIdentity.value;
    formData.append("initiator_identity_type", effectiveInitiatorIdentity);

    if (effectiveInitiatorIdentity === "ARTIST") {
      const artistIdToUse =
        payload.initiator_artist_profile_id ||
        activeArtistProfileIdForChat.value;
      if (artistIdToUse) {
        formData.append("initiator_artist_profile_id", String(artistIdToUse));
      } else {
        error.value = "Artist profile ID missing for sending as artist.";
        isSendingMessage.value = false;
        return null;
      }
    }

    try {
      const response = await axios.post<Conversation>(
        "/chat/conversations/send-initial-message/",
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      const newOrUpdatedConversation = response.data;
      const index = conversations.value.findIndex(
        (c) => c.id === newOrUpdatedConversation.id
      );
      if (index !== -1) {
        conversations.value[index] = newOrUpdatedConversation;
      } else {
        conversations.value.unshift(newOrUpdatedConversation);
      }
      conversations.value.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
      return newOrUpdatedConversation;
    } catch (err: any) {
      console.error("Chat Store: Failed to send initial message:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail ||
          Object.values(err.response.data).flat().join(" ") || // Flatten if errors are arrays
          "Failed to send message.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return null;
    } finally {
      isSendingMessage.value = false;
    }
  }

  async function sendReply(
    conversationId: number,
    payload: ReplyMessagePayload
  ): Promise<boolean> {
    if (!authStore.isLoggedIn) {
      error.value = "You must be logged in to send messages.";
      return false;
    }
    isSendingMessage.value = true;
    error.value = null;
    const formData = new FormData();
    if (payload.text) formData.append("text", payload.text);
    if (payload.attachment) formData.append("attachment", payload.attachment);
    formData.append("message_type", payload.message_type || "TEXT");

    try {
      const response = await axios.post<Conversation>(
        `/chat/conversations/${conversationId}/reply/`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      const updatedConversation = response.data;
      const convIndex = conversations.value.findIndex(
        (c) => c.id === conversationId
      );
      if (convIndex !== -1) {
        conversations.value[convIndex] = updatedConversation;
      } else {
        // This case should ideally not happen for a reply, but handle defensively
        conversations.value.unshift(updatedConversation);
      }

      if (
        activeConversationId.value === conversationId &&
        updatedConversation.latest_message
      ) {
        const existingMsgIndex = activeConversationMessages.value.findIndex(
          (m) => m.id === updatedConversation.latest_message!.id
        );
        if (existingMsgIndex === -1) {
          // New message
          activeConversationMessages.value.push(
            updatedConversation.latest_message
          );
        } else {
          // Message might have been optimistic UI, now confirmed
          activeConversationMessages.value[existingMsgIndex] =
            updatedConversation.latest_message;
        }
      }
      // Re-sort conversations by updated_at
      conversations.value.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
      return true;
    } catch (err: any) {
      console.error(
        `Chat Store: Failed to send reply to conv ${conversationId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail ||
          Object.values(err.response.data).flat().join(" ") ||
          "Failed to send reply.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isSendingMessage.value = false;
    }
  }

  async function acceptChatRequest(conversationId: number): Promise<boolean> {
    if (!authStore.isLoggedIn) return false;
    error.value = null;
    // Optimistically update frontend first for better UX
    const conversation = conversations.value.find(
      (c) => c.id === conversationId
    );
    let originalAcceptedState = false;
    if (conversation) {
      originalAcceptedState = conversation.is_accepted;
      conversation.is_accepted = true; // Optimistic update
      // if (activeConversationId.value === conversationId) {
      //      // Potentially refresh messages or update conversation details in active view
      // }
    }

    try {
      const response = await axios.post<Conversation>(
        `/chat/conversations/${conversationId}/accept-request/`
      );
      const updatedConversation = response.data; // Backend confirms the update
      const index = conversations.value.findIndex(
        (c) => c.id === conversationId
      );
      if (index !== -1) {
        conversations.value[index] = updatedConversation;
        if (activeConversationId.value === conversationId) {
          // If this conversation is active, refresh messages to mark them read
          await fetchMessagesForConversation(conversationId);
        }
      }
      return true;
    } catch (err: any) {
      console.error(
        `Chat Store: Failed to accept request for conv ${conversationId}:`,
        err
      );
      if (conversation) {
        conversation.is_accepted = originalAcceptedState; // Revert optimistic update
      }
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail ||
          err.response.data.error ||
          "Failed to accept request.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    }
  }

  function addMessageToActiveConversation(message: ChatMessage) {
    if (activeConversationId.value === message.conversation) {
      // Avoid adding duplicates if message comes via WebSocket and also HTTP response
      if (!activeConversationMessages.value.find((m) => m.id === message.id)) {
        activeConversationMessages.value.push(message);
      }
      // If message is from other user and current user is viewing, mark as read (on FE)
      // Backend will handle DB update when messages are fetched next time or via explicit call.
      const conversation = conversations.value.find(
        (c) => c.id === activeConversationId.value
      );
      if (conversation && message.sender_user.id !== authStore.authUser?.id) {
        message.is_read = true; // Frontend reflects read status
        if (conversation.unread_count > 0) {
          conversation.unread_count--;
        }
      }
    }
    // Update latest message in the main conversations list
    const convInList = conversations.value.find(
      (c) => c.id === message.conversation
    );
    if (convInList) {
      convInList.latest_message = message;
      convInList.updated_at = message.timestamp; // Ensure updated_at reflects latest message time
      // Increment unread count if message is not from current user AND conversation is not active
      if (
        message.sender_user.id !== authStore.authUser?.id &&
        activeConversationId.value !== message.conversation &&
        !message.is_read
      ) {
        convInList.unread_count = (convInList.unread_count || 0) + 1;
      }
      // Re-sort conversations by updated_at
      conversations.value.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
    }
  }

  function clearActiveConversation() {
    activeConversationId.value = null;
    activeConversationMessages.value = [];
  }

  // Reset store on logout
  authStore.$subscribe((mutation, state) => {
    if (!state.isLoggedIn) {
      conversations.value = [];
      activeConversationMessages.value = [];
      activeConversationId.value = null;
      currentChatViewIdentity.value = "USER";
      error.value = null;
    }
  });

  const pendingUserRequests = computed(() => {
    if (currentChatViewIdentity.value !== "USER" || !authStore.authUser)
      return [];
    return displayedConversations.value.filter(
      (conv) =>
        !conv.is_accepted && conv.initiator_user?.id !== authStore.authUser?.id
    );
  });

  const acceptedUserConversations = computed(() => {
    if (currentChatViewIdentity.value !== "USER" || !authStore.authUser)
      return [];
    return displayedConversations.value.filter(
      (conv) =>
        conv.is_accepted || conv.initiator_user?.id === authStore.authUser?.id
    );
  });

  const pendingArtistRequests = computed(() => {
    if (
      currentChatViewIdentity.value !== "ARTIST" ||
      !authStore.authUser ||
      !activeArtistProfileIdForChat.value
    )
      return [];
    return displayedConversations.value.filter(
      (conv) =>
        !conv.is_accepted && conv.initiator_user?.id !== authStore.authUser?.id
      // Additional check: ensure it's really a request *to* this artist identity if needed
    );
  });

  const acceptedArtistConversations = computed(() => {
    if (
      currentChatViewIdentity.value !== "ARTIST" ||
      !authStore.authUser ||
      !activeArtistProfileIdForChat.value
    )
      return [];
    return displayedConversations.value.filter(
      (conv) =>
        conv.is_accepted ||
        (conv.initiator_user?.id === authStore.authUser?.id &&
          conv.initiator_artist_profile_details?.id ===
            activeArtistProfileIdForChat.value)
    );
  });

  return {
    conversations,
    activeConversationMessages,
    activeConversationId,
    isLoadingConversations,
    isLoadingMessages,
    isSendingMessage,
    error,
    currentChatViewIdentity, // expose new state
    activeArtistProfileIdForChat, // expose for convenience
    setActiveChatViewIdentity, // expose action
    displayedConversations, // expose new computed
    fetchConversations,
    fetchMessagesForConversation,
    sendInitialMessage,
    sendReply,
    acceptChatRequest,
    clearActiveConversation,
    addMessageToActiveConversation,
    pendingUserRequests,
    acceptedUserConversations,
    pendingArtistRequests,
    acceptedArtistConversations,
  };
});
