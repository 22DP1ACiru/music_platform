export interface ArtistInfo {
  id: number;
  name: string;
  user_id: number;
  artist_picture?: string | null;
}

export interface TrackInfoFromApi {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string;
  stream_url: string;
  genres_data?: { id: number; name: string }[];
  release_id?: number;
  artist_id?: number;
  artist_name?: string;
  release_title?: string;
  release_cover_art?: string | null;
  listen_count?: number;
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
  listen_count?: number;
}

export interface ReleaseSummary {
  id: number;
  title: string;
  artist: ArtistInfo | null;
  cover_art: string | null;
  release_type: string;
  release_type_display?: string;
  listen_count?: number;
}

export interface CarouselSlide {
  id: string | number;
  type: "welcome" | "release";
  title: string;
  subtitle?: string;
  description?: string;
  imageUrl?: string | null;
  linkUrl?: string;
  releaseObject?: ReleaseDetail | ReleaseSummary;
}

export interface HighlightItem {
  // This is the raw data from /api/highlights/
  id: number;
  release_id: number;
  release_title: string;
  release_artist_name: string;
  effective_title: string;
  title: string; // Previously carousel_title
  subtitle?: string | null; // Previously carousel_subtitle
  description?: string | null; // Previously carousel_description
  effective_image_url: string | null;
  order: number;
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
  initiator_user: UserChatInfo | null;
  initiator_identity_type: "USER" | "ARTIST";
  initiator_artist_profile_details: ArtistChatInfo | null;
  related_artist_recipient_details: ArtistChatInfo | null;
  created_at: string;
  updated_at: string;
  latest_message: ChatMessage | null;
  unread_count: number;
  other_participant_display_name: string | null;
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

export interface OrderItemDetail {
  id: number;
  product_name: string;
  quantity: number;
  price_at_purchase: string;
}

export interface OrderDetail {
  id: number;
  user: string;
  email: string | null;
  status: string;
  status_display: string;
  total_amount: string;
  currency: string;
  created_at: string;
  updated_at: string;
  payment_gateway_id: string | null;
  items: OrderItemDetail[];
}

export interface Playlist {
  id: number;
  title: string;
  owner: string;
  tracks: TrackInfoFromApi[];
  track_count: number;
  cover_art: string | null;
  description: string | null;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  artist?: ArtistInfo;
}
