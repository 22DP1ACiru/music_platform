// From ReleaseDetailView.vue
export interface ArtistInfo {
  id: number;
  name: string;
  user_id: number; // Assuming user_id is part of artist info for ownership checks
}

export interface TrackInfoFromApi {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string; // Original upload path
  stream_url: string; // Streaming URL
  genres_data?: { id: number; name: string }[];
}

export interface ReleaseDetail {
  id: number;
  title: string;
  artist: ArtistInfo;
  product_info_id: number | null;
  tracks: TrackInfoFromApi[];
  cover_art: string | null;
  release_type: string;
  release_type_display: string;
  release_date: string;
  description?: string;
  genres_data?: { id: number; name: string }[];
  is_published: boolean;
  pricing_model: "FREE" | "PAID" | "NYP";
  pricing_model_display: string;
  price: string | null;
  currency: string | null;
  minimum_price_nyp: string | null;
  available_download_formats: { value: string; label: string }[];
}

export interface GeneratedDownloadStatus {
  id: number;
  unique_identifier: string;
  release: number; // Release ID
  release_title: string;
  user: number;
  requested_format: string;
  requested_format_display: string;
  status: "PENDING" | "PROCESSING" | "READY" | "FAILED" | "EXPIRED";
  celery_task_id: string | null;
  download_url: string | null;
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  failure_reason: string | null;
}

// Player related types if they become complex and shared
export interface PlayerTrackInfo {
  id: number;
  title: string;
  audio_file: string;
  artistName?: string;
  releaseTitle?: string;
  coverArtUrl?: string | null;
  duration?: number | null;
}

// --- CART TYPES ---
export interface ProductSummaryForCart {
  id: number;
  name: string;
  price: string;
  currency: string;
  cover_art?: string | null;
  release_title?: string | null;
  artist_name?: string | null;
  release_id?: number | null;
}

export interface CartItem {
  id: number;
  product: ProductSummaryForCart;
  price_override: string | null;
  added_at: string;
  effective_price_original_currency: string;
  original_currency: string;
  effective_price_settlement_currency: string | null;
}

export interface Cart {
  id: number;
  user: string;
  items: CartItem[];
  total_price: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

// --- CHAT TYPES ---
export interface UserChatInfo {
  // Basic user info for chat
  id: number;
  username: string;
  // profile?: { profile_picture: string | null }; // Optional: if you want to show profile pics
}

export interface ArtistChatInfo {
  // Info for an artist context in chat
  id: number;
  name: string;
  artist_picture: string | null;
}

export interface ChatMessage {
  id: number;
  conversation: number;
  sender: UserChatInfo;
  text: string | null;
  attachment?: string | null;
  attachment_url?: string | null;
  original_attachment_filename?: string | null;
  message_type: "TEXT" | "AUDIO" | "VOICE" | "TRACK_SHARE";
  timestamp: string;
  is_read: boolean;
}

export interface Conversation {
  id: number;
  participants: UserChatInfo[];
  is_accepted: boolean;
  initiator: UserChatInfo | null;
  related_artist: ArtistChatInfo | null; // New field
  created_at: string;
  updated_at: string;
  latest_message: ChatMessage | null;
  unread_count: number;
  other_participant_username: string | null; // Helper from backend
}

export interface CreateMessagePayload {
  recipient_user_id?: number | null;
  recipient_artist_id?: number | null;
  text?: string | null;
  attachment?: File | null;
  message_type?: "TEXT" | "AUDIO" | "VOICE";
}

// Type for OrderDetail, assuming it's used in OrderHistoryView etc.
// This should match the structure your backend's OrderSerializer provides.
export interface OrderItemDetail {
  id: number;
  product_name: string;
  quantity: number;
  price_at_purchase: string; // Decimal as string
  // any other fields for order item...
}

export interface OrderDetail {
  id: number;
  user: string; // Username or ID
  status: string;
  total_amount: string; // Decimal as string
  currency: string;
  created_at: string;
  updated_at: string;
  items: OrderItemDetail[]; // Array of order items
  // any other fields for order...
}
