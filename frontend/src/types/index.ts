export interface ArtistInfo {
  id: number;
  name: string;
  user_id: number; // ID of the User model that owns this Artist
  artist_picture?: string | null; // Add artist_picture here if ArtistInfo is used for avatars
}

export interface TrackInfoFromApi {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string; // This is likely the storage path, not stream URL
  stream_url: string; // This is the one for playing
  genres_data?: { id: number; name: string }[];
}

export interface ReleaseDetail {
  id: number;
  title: string;
  artist: ArtistInfo; // ArtistInfo should include id and name
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
  release: number;
  release_title: string;
  user: number; // User ID
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

export interface PlayerTrackInfo {
  id: number; // Track ID
  title: string;
  audio_file: string; // Stream URL
  artistName?: string;
  releaseTitle?: string;
  coverArtUrl?: string | null;
  duration?: number | null;
}

export interface ProductSummaryForCart {
  id: number; // Product ID
  name: string; // Usually Release title
  price: string; // Default price of the product
  currency: string;
  cover_art?: string | null;
  release_title?: string | null;
  artist_name?: string | null;
  release_id?: number | null; // ID of the related Release
}

export interface CartItem {
  id: number; // CartItem ID
  product: ProductSummaryForCart;
  price_override: string | null; // For NYP
  added_at: string;
  effective_price_original_currency: string;
  original_currency: string;
  effective_price_settlement_currency: string | null; // If prices are converted
}

export interface Cart {
  id: number; // Cart ID
  user: string; // Username
  items: CartItem[];
  total_price: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

// --- CHAT TYPES ---
export interface UserChatInfo {
  id: number;
  username: string;
  // profile_picture?: string | null; // Consider adding for avatars
}

export interface ArtistChatInfo {
  id: number;
  name: string;
  artist_picture: string | null;
}

export interface ChatMessage {
  id: number;
  conversation: number;
  sender_user: UserChatInfo; // The actual User model that sent it
  sender_identity_type: "USER" | "ARTIST"; // The identity used for THIS message
  sending_artist_details: ArtistChatInfo | null; // If sender_identity_type is ARTIST
  text: string | null;
  attachment?: string | null; // Raw attachment path (less used by frontend directly)
  attachment_url?: string | null; // URL to download/stream attachment
  original_attachment_filename?: string | null;
  message_type: "TEXT" | "AUDIO" | "VOICE" | "TRACK_SHARE";
  timestamp: string;
  is_read: boolean;
}

export interface Conversation {
  id: number;
  participants: UserChatInfo[]; // The User models involved in this conversation
  is_accepted: boolean;
  initiator_user: UserChatInfo | null; // The User model who created the conversation
  initiator_identity_type: "USER" | "ARTIST"; // The identity the initiator_user chose
  initiator_artist_profile_details: ArtistChatInfo | null; // If initiator chose ARTIST
  related_artist_recipient_details: ArtistChatInfo | null; // If conversation is TO an artist
  created_at: string;
  updated_at: string;
  latest_message: ChatMessage | null;
  unread_count: number;
  other_participant_display_name: string | null; // Name to display for the other party
}

export interface CreateMessagePayload {
  recipient_user_id?: number | null;
  recipient_artist_id?: number | null;
  text?: string | null;
  attachment?: File | null;
  message_type?: "TEXT" | "AUDIO" | "VOICE";
  initiator_identity_type?: "USER" | "ARTIST";
  initiator_artist_profile_id?: number | null;
}

export type ReplyMessagePayload = Pick<
  CreateMessagePayload,
  "text" | "attachment" | "message_type"
>;
// --- END CHAT TYPES ---

export interface OrderItemDetail {
  id: number;
  product_name: string; // Name of the product (e.g., release title)
  quantity: number; // Should always be 1 for digital items
  price_at_purchase: string; // Price paid for this item
}

export interface OrderDetail {
  id: number;
  user: string; // Username of the buyer
  status: string; // e.g., PENDING, COMPLETED, FAILED
  total_amount: string; // Total amount of the order
  currency: string; // Currency of the order
  created_at: string;
  updated_at: string;
  items: OrderItemDetail[]; // List of items in the order
}
