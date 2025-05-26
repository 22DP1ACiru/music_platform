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

// From LibraryView.vue (if specific types needed, but LibraryItem uses ReleaseDetail)
// If TrackInfoFromApi is defined in LibraryItem's ReleaseDetail, ensure it's consistent.

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

// --- NEW CART TYPES ---
export interface ProductSummaryForCart {
  id: number;
  name: string;
  price: string; // Assuming price is a string from backend (decimal)
  currency: string;
  cover_art?: string | null; // Assuming ProductSerializer might provide this via release
  release_title?: string | null; // From ProductSerializer
  artist_name?: string | null; // Assuming ProductSerializer might get this via release.artist
  release_id?: number | null;
}

export interface CartItem {
  id: number;
  product: ProductSummaryForCart; // Nested Product details
  price_override: string | null; // Decimal as string
  added_at: string;
  effective_price: string; // Decimal as string
}

export interface Cart {
  id: number;
  user: string; // Username
  items: CartItem[];
  total_price: string; // Decimal as string
  currency: string;
  created_at: string;
  updated_at: string;
}
// --- END NEW CART TYPES ---
