import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import { useAuthStore } from "./auth";
import type {
  Conversation,
  ChatMessage,
  CreateMessagePayload, // For initiating
  ReplyMessagePayload, // For replies
} from "@/types";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const useChatStore = defineStore("chat", () => {
  const authStore = useAuthStore();

  const conversations = ref<Conversation[]>([]);
  const activeConversationMessages = ref<ChatMessage[]>([]);
  const activeConversationId = ref<number | null>(null);

  const isLoadingConversations = ref(false);
  const isLoadingMessages = ref(false);
  const isSendingMessage = ref(false);
  const error = ref<string | null>(null);

  const userDirectMessages = computed(() => {
    // User DMs:
    // 1. No related_artist_recipient (standard user-to-user)
    // 2. OR, related_artist_recipient IS NOT ME, and I initiated as USER
    // 3. OR, related_artist_recipient IS ME, and other user initiated as USER (or Artist, but displayed in my User DMs)
    // This logic can get complex for presentation.
    // A simpler approach for "My DMs" tab:
    // - Initiated by me as USER
    // - Initiated towards me as USER (related_artist_recipient is null, and initiator is not me)
    return conversations.value.filter((conv) => {
      // Standard User-to-User DM (no artist involved as recipient)
      if (!conv.related_artist_recipient_details) return true;
      // If I initiated it as USER towards an ARTIST, it's still from "My User DM" perspective
      if (
        conv.initiator_user?.id === authStore.authUser?.id &&
        conv.initiator_identity_type === "USER" &&
        conv.related_artist_recipient_details
      ) {
        return true;
      }
      return false;
    });
  });

  const artistDirectMessages = computed(() => {
    if (
      !authStore.isLoggedIn ||
      !authStore.hasArtistProfile ||
      !authStore.artistProfileId
    ) {
      return [];
    }
    // Artist DMs:
    // 1. Initiated by me as ARTIST
    // 2. Initiated towards my ARTIST profile
    return conversations.value.filter((conv) => {
      if (
        conv.initiator_user?.id === authStore.authUser?.id &&
        conv.initiator_identity_type === "ARTIST" &&
        conv.initiator_artist_profile_details?.id === authStore.artistProfileId
      ) {
        return true; // I initiated as this artist
      }
      if (
        conv.related_artist_recipient_details?.id === authStore.artistProfileId
      ) {
        return true; // DM is to my artist profile
      }
      return false;
    });
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
        conversation.unread_count = 0;
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

    // Use updated field names for initiator identity
    formData.append(
      "initiator_identity_type",
      payload.initiator_identity_type || "USER"
    );
    if (
      payload.initiator_identity_type === "ARTIST" &&
      payload.initiator_artist_profile_id
    ) {
      formData.append(
        "initiator_artist_profile_id",
        String(payload.initiator_artist_profile_id)
      );
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
      if (index !== -1) conversations.value[index] = newOrUpdatedConversation;
      else conversations.value.unshift(newOrUpdatedConversation);

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
          Object.values(err.response.data).join(" ") ||
          "Failed to send message.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return null;
    } finally {
      isSendingMessage.value = false;
    }
  }

  // sendReply now uses ReplyMessagePayload (simpler)
  async function sendReply(
    conversationId: number,
    payload: ReplyMessagePayload // Does not include sender identity fields
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

    // Sender identity is NOT sent from client for replies; backend determines it.

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
      if (convIndex !== -1)
        conversations.value[convIndex] = updatedConversation;

      if (
        activeConversationId.value === conversationId &&
        updatedConversation.latest_message
      ) {
        const existingMsgIndex = activeConversationMessages.value.findIndex(
          (m) => m.id === updatedConversation.latest_message!.id
        );
        if (existingMsgIndex === -1) {
          activeConversationMessages.value.push(
            updatedConversation.latest_message
          );
        }
      }
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
          Object.values(err.response.data).join(" ") ||
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
    try {
      const response = await axios.post<Conversation>(
        `/chat/conversations/${conversationId}/accept-request/`
      );
      const updatedConversation = response.data;
      const index = conversations.value.findIndex(
        (c) => c.id === conversationId
      );
      if (index !== -1) conversations.value[index] = updatedConversation;
      return true;
    } catch (err: any) {
      console.error(
        `Chat Store: Failed to accept request for conv ${conversationId}:`,
        err
      );
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

  function clearActiveConversation() {
    activeConversationId.value = null;
    activeConversationMessages.value = [];
  }

  return {
    conversations,
    userDirectMessages,
    artistDirectMessages,
    activeConversationMessages,
    activeConversationId,
    isLoadingConversations,
    isLoadingMessages,
    isSendingMessage,
    error,
    fetchConversations,
    fetchMessagesForConversation,
    sendInitialMessage,
    sendReply,
    acceptChatRequest,
    clearActiveConversation,
  };
});
