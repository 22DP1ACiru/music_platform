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
    if (!authStore.authUser) return [];
    const currentUserId = authStore.authUser.id;
    const currentUserArtistId = authStore.artistProfileId; // Can be null

    return conversations.value.filter((conv) => {
      // Scenario 1: Conversation initiated by me as "USER"
      if (
        conv.initiator_user?.id === currentUserId &&
        conv.initiator_identity_type === "USER"
      ) {
        return true;
      }

      // Scenario 2: Conversation initiated by someone else
      if (conv.initiator_user?.id !== currentUserId) {
        // Subcase 2a: DM to me as "USER" (no specific artist recipient)
        if (!conv.related_artist_recipient_details) {
          return true;
        }
        // Subcase 2b: DM to MY artist profile, but initiated by a "USER"
        if (
          conv.related_artist_recipient_details?.id === currentUserArtistId &&
          conv.initiator_identity_type === "USER"
        ) {
          return true;
        }
      }
      return false;
    });
  });

  const artistDirectMessages = computed(() => {
    if (
      !authStore.hasArtistProfile ||
      !authStore.artistProfileId ||
      !authStore.authUser
    ) {
      return [];
    }
    const currentUserId = authStore.authUser.id;
    const currentArtistId = authStore.artistProfileId;

    return conversations.value.filter((conv) => {
      // Scenario 1: Conversation initiated by me AS THIS ARTIST
      if (
        conv.initiator_user?.id === currentUserId &&
        conv.initiator_identity_type === "ARTIST" &&
        conv.initiator_artist_profile_details?.id === currentArtistId
      ) {
        return true;
      }

      // Scenario 2: Conversation is directed TO THIS ARTIST profile (initiated by anyone, including another artist)
      if (conv.related_artist_recipient_details?.id === currentArtistId) {
        // We need to ensure it wasn't a User DMing my Artist profile, as that's handled by userDirectMessages
        if (conv.initiator_identity_type === "ARTIST") {
          return true; // Artist-to-MyArtist
        }
        // If User DMed my Artist, it's already in userDirectMessages.
        // However, if the requirement is that DMs *to* my artist always show here, regardless of who sent, then:
        // return true; // This would make User-to-MyArtist appear in both tabs.
        // The current filtering in `userDirectMessages` (Subcase 2b) aims to put User-to-MyArtist in User DMs.
        // So, for Artist DMs, we only want Artist-to-MyArtist if received.
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
          activeConversationMessages.value.push(
            updatedConversation.latest_message
          );
        } else {
          activeConversationMessages.value[existingMsgIndex] =
            updatedConversation.latest_message;
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
      if (index !== -1) {
        conversations.value[index] = updatedConversation;
        if (activeConversationId.value === conversationId) {
          fetchMessagesForConversation(conversationId);
        }
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

  function addMessageToActiveConversation(message: ChatMessage) {
    if (activeConversationId.value === message.conversation) {
      if (!activeConversationMessages.value.find((m) => m.id === message.id)) {
        activeConversationMessages.value.push(message);
      }
      const conversation = conversations.value.find(
        (c) => c.id === activeConversationId.value
      );
      if (conversation && message.sender_user.id !== authStore.authUser?.id) {
        message.is_read = true;
        if (conversation.unread_count > 0) {
          conversation.unread_count--;
        }
      }
    }
    const convInList = conversations.value.find(
      (c) => c.id === message.conversation
    );
    if (convInList) {
      convInList.latest_message = message;
      convInList.updated_at = message.timestamp;
      if (
        message.sender_user.id !== authStore.authUser?.id &&
        activeConversationId.value !== message.conversation &&
        !message.is_read
      ) {
        convInList.unread_count = (convInList.unread_count || 0) + 1;
      }
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
    addMessageToActiveConversation,
  };
});
