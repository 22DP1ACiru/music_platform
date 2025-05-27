export interface ArtistInfo {
  id: number;
  name: string;
  user_id: number;
}

export interface TrackInfoFromApi {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string;
  stream_url: string;
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
  release: number;
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

export interface PlayerTrackInfo {
  id: number;
  title: string;
  audio_file: string;
  artistName?: string;
  releaseTitle?: string;
  coverArtUrl?: string | null;
  duration?: number | null;
}

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

export interface UserChatInfo {
  id: number;
  username: string;
}

export interface ArtistChatInfo {
  id: number;
  name: string;
  artist_picture: string | null;
}

export interface ChatMessage {
  id: number;
  conversation: number;
  sender_user: UserChatInfo;
  sender_identity_type: "USER" | "ARTIST";
  sending_artist_details: ArtistChatInfo | null;
  text: string | null;
  attachment?: string | null;
  attachment_url?: string | null;
  original_attachment_filename?: string | null;
  message_type: "TEXT" | "AUDIO" | "VOICE" | "TRACK_SHARE";
  timestamp: string;
  is_read: boolean;
}

// For Conversation, add initiator identity fields
export interface Conversation {
  id: number;
  participants: UserChatInfo[];
  is_accepted: boolean;
  initiator_user: UserChatInfo | null; // Changed from initiator
  initiator_identity_type: "USER" | "ARTIST"; // Added
  initiator_artist_profile_details: ArtistChatInfo | null; // Added
  related_artist_recipient_details: ArtistChatInfo | null; // Changed from related_artist
  created_at: string;
  updated_at: string;
  latest_message: ChatMessage | null;
  unread_count: number;
  other_participant_username: string | null; // This will need careful re-evaluation based on new identity model
}

// Updated CreateMessagePayload for INITIATING conversations
export interface CreateMessagePayload {
  recipient_user_id?: number | null;
  recipient_artist_id?: number | null; // This refers to the ID of the Artist being targeted
  text?: string | null;
  attachment?: File | null;
  message_type?: "TEXT" | "AUDIO" | "VOICE";
  // Fields for the INITIATOR's identity
  initiator_identity_type?: "USER" | "ARTIST"; // Changed from sender_identity_type
  initiator_artist_profile_id?: number | null; // Changed from sending_artist_id (ID of user's own artist profile)
}

// Payload for REPLIES will be simpler, not needing recipient or initiator identity fields
export type ReplyMessagePayload = Pick<
  CreateMessagePayload,
  "text" | "attachment" | "message_type"
>;

export interface OrderItemDetail {
  id: number;
  product_name: string;
  quantity: number;
  price_at_purchase: string;
}

export interface OrderDetail {
  id: number;
  user: string;
  status: string;
  total_amount: string;
  currency: string;
  created_at: string;
  updated_at: string;
  items: OrderItemDetail[];
}
