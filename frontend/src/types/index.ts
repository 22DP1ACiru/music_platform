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
