import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import { useAuthStore } from "./auth";
import type { Conversation, ChatMessage, CreateMessagePayload } from "@/types";

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
    return conversations.value.filter((conv) => !conv.related_artist);
  });

  const artistDirectMessages = computed(() => {
    if (!authStore.isLoggedIn || !authStore.hasArtistProfile) {
      return [];
    }
    return conversations.value.filter((conv) => conv.related_artist);
  });

  async function fetchConversations() {
    if (!authStore.isLoggedIn) return;
    isLoadingConversations.value = true;
    error.value = null;
    try {
      // Expect a paginated response for conversations
      const response = await axios.get<PaginatedResponse<Conversation>>( // Adjusted type here
        "/chat/conversations/"
      );
      // Access the .results array for sorting and assignment
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
    if (payload.text) {
      formData.append("text", payload.text);
    }
    if (payload.attachment) {
      formData.append("attachment", payload.attachment);
    }
    formData.append("message_type", payload.message_type || "TEXT");

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

  async function sendReply(
    conversationId: number,
    payload: Omit<
      CreateMessagePayload,
      "recipient_user_id" | "recipient_artist_id"
    >
  ): Promise<boolean> {
    if (!authStore.isLoggedIn) {
      error.value = "You must be logged in to send messages.";
      return false;
    }
    isSendingMessage.value = true;
    error.value = null;
    const formData = new FormData();
    if (payload.text) {
      formData.append("text", payload.text);
    }
    if (payload.attachment) {
      formData.append("attachment", payload.attachment);
    }
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
      }
      if (
        activeConversationId.value === conversationId &&
        updatedConversation.latest_message
      ) {
        activeConversationMessages.value.push(
          updatedConversation.latest_message
        );
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
      if (index !== -1) {
        conversations.value[index] = updatedConversation;
      }
      // If this is the currently active conversation, refresh its messages or state
      if (activeConversationId.value === conversationId) {
        // Potentially re-fetch messages or update local state to reflect acceptance
        // For now, just updating the conversation in the list is fine.
        // If messages view depends on `activeConversation.value.is_accepted`, it will update.
      }
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
