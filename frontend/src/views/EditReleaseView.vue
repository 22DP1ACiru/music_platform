<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";

// --- Interfaces ---
interface TrackData {
  // For frontend state management
  id: number; // Temporary frontend ID for new tracks, DB ID for existing
  title: string;
  track_number: number | null;
  audio_file: string | null; // URL for existing, or name for new (display only)
  genre_names: string[];
  _isNew?: boolean;
  _isRemoved?: boolean;
  _audioFileObject?: File | null; // Actual file object for new/updated files
  _originalId?: number; // DB ID for existing tracks, to ensure correct PATCH/DELETE
}

interface ReleaseApiResponseData {
  // To map backend response
  id: number;
  title: string;
  release_type: "ALBUM" | "EP" | "SINGLE";
  release_date: string; // ISO string from backend
  cover_art: string | null;
  genres_data: { id: number; name: string }[];
  is_published: boolean;
  tracks: {
    // Tracks as they come from API
    id: number;
    title: string;
    track_number: number | null;
    audio_file: string; // URL
    duration_in_seconds: number | null;
    genres_data?: { id: number; name: string }[];
  }[];
}

const releaseFormData = reactive({
  id: null as number | null,
  title: "",
  release_type: "ALBUM" as "ALBUM" | "EP" | "SINGLE",
  release_date_str: "", // For date input
  release_time_str: "", // For time input
  cover_art_url: null as string | null, // URL of current cover art for display
  new_cover_art_file: null as File | null, // For uploading new cover art
  genre_names: [] as string[],
  is_published: true,
  tracks: [] as TrackData[], // Local state for tracks being edited/added
});

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const availableGenres = ref<{ id: number; name: string }[]>([]);
const newReleaseGenre = ref("");
const newTrackGenres = ref<string[]>([]); // For new genre inputs for each track

const isLoading = ref(true);
const isSubmitting = ref(false);
const error = ref<string | null>(null);
const trackIdCounter = ref(Date.now()); // For unique keys for new tracks in v-for

const fullReleaseDateTime = computed(() => {
  if (releaseFormData.release_date_str && releaseFormData.release_time_str) {
    const localDateTime = new Date(
      `${releaseFormData.release_date_str}T${releaseFormData.release_time_str}`
    );
    return isNaN(localDateTime.getTime()) ? null : localDateTime.toISOString();
  }
  if (releaseFormData.release_date_str) {
    const localDate = new Date(releaseFormData.release_date_str + "T00:00:00");
    return isNaN(localDate.getTime()) ? null : localDate.toISOString();
  }
  return null;
});

const fetchReleaseData = async (releaseId: string) => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await axios.get<ReleaseApiResponseData>(
      `/releases/${releaseId}/`
    );
    const data = response.data;

    releaseFormData.id = data.id;
    releaseFormData.title = data.title;
    releaseFormData.release_type = data.release_type;

    const releaseDateObj = new Date(data.release_date);
    releaseFormData.release_date_str = releaseDateObj
      .toISOString()
      .split("T")[0];
    releaseFormData.release_time_str = `${releaseDateObj
      .getHours()
      .toString()
      .padStart(2, "0")}:${releaseDateObj
      .getMinutes()
      .toString()
      .padStart(2, "0")}`;

    releaseFormData.cover_art_url = data.cover_art;
    releaseFormData.new_cover_art_file = null; // Reset any pending new file
    releaseFormData.is_published = data.is_published;
    releaseFormData.genre_names = data.genres_data.map((g) => g.name);

    newTrackGenres.value = []; // Reset
    releaseFormData.tracks = data.tracks.map((apiTrack) => {
      newTrackGenres.value.push(""); // Placeholder for this track's genre input
      return {
        id: apiTrack.id, // DB ID
        _originalId: apiTrack.id, // Store DB ID for PATCH/DELETE
        title: apiTrack.title,
        track_number: apiTrack.track_number,
        audio_file: apiTrack.audio_file, // URL of existing audio file
        genre_names: apiTrack.genres_data
          ? apiTrack.genres_data.map((g) => g.name)
          : [],
        _isNew: false,
        _isRemoved: false,
        _audioFileObject: null, // No new file object initially
      };
    });
  } catch (err: any) {
    console.error("Failed to fetch release data:", err);
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      error.value = "Release not found.";
    } else if (axios.isAxiosError(err) && err.response?.status === 403) {
      error.value = "You are not authorized to edit this release.";
    } else {
      error.value = "Could not load release details for editing.";
    }
  } finally {
    isLoading.value = false;
  }
};

const fetchGenres = async () => {
  try {
    const response = await axios.get("/genres/");
    availableGenres.value = response.data;
  } catch (err) {
    console.error("Failed to fetch genres:", err);
  }
};

onMounted(async () => {
  const releaseId = route.params.id as string;
  if (releaseId) {
    await fetchGenres(); // Fetch genres first or concurrently
    await fetchReleaseData(releaseId);
  } else {
    error.value = "No release ID provided for editing.";
    isLoading.value = false;
  }
});

const addReleaseGenreChip = () => {
  const genreToAdd = newReleaseGenre.value.trim();
  if (genreToAdd && !releaseFormData.genre_names.includes(genreToAdd)) {
    releaseFormData.genre_names.push(genreToAdd);
  }
  newReleaseGenre.value = "";
};
const removeReleaseGenreChip = (index: number) => {
  releaseFormData.genre_names.splice(index, 1);
};

const addTrackGenreChip = (trackIndex: number) => {
  const genreToAdd = newTrackGenres.value[trackIndex]?.trim();
  if (
    genreToAdd &&
    !releaseFormData.tracks[trackIndex].genre_names.includes(genreToAdd)
  ) {
    releaseFormData.tracks[trackIndex].genre_names.push(genreToAdd);
  }
  if (newTrackGenres.value[trackIndex] !== undefined) {
    newTrackGenres.value[trackIndex] = "";
  }
};
const removeTrackGenreChip = (trackIndex: number, genreChipIndex: number) => {
  releaseFormData.tracks[trackIndex]?.genre_names.splice(genreChipIndex, 1);
};

const addTrack = () => {
  const newTrackNumber =
    releaseFormData.tracks.filter((t) => !t._isRemoved).length + 1;
  releaseFormData.tracks.push({
    id: trackIdCounter.value++, // Temporary frontend ID
    _originalId: undefined, // No original ID as it's new
    title: "",
    track_number: newTrackNumber,
    audio_file: null, // No existing audio file URL
    genre_names: [],
    _isNew: true,
    _isRemoved: false,
    _audioFileObject: null, // Placeholder for new file
  });
  newTrackGenres.value.push("");
};

const markTrackForRemoval = (index: number) => {
  const track = releaseFormData.tracks[index];
  if (track) {
    if (track._isNew) {
      // If it's a new track not yet saved, remove it directly
      releaseFormData.tracks.splice(index, 1);
      newTrackGenres.value.splice(index, 1);
    } else {
      // If it's an existing track, mark for removal
      track._isRemoved = true;
    }
    // Re-number visible tracks
    let visibleTrackCounter = 1;
    releaseFormData.tracks.forEach((t) => {
      if (!t._isRemoved) {
        t.track_number = visibleTrackCounter++;
      }
    });
  }
};
const unmarkTrackForRemoval = (index: number) => {
  const track = releaseFormData.tracks[index];
  if (track && !track._isNew) {
    // Can only unmark existing tracks
    track._isRemoved = false;
  }
  // Re-number visible tracks
  let visibleTrackCounter = 1;
  releaseFormData.tracks.forEach((t) => {
    if (!t._isRemoved) {
      t.track_number = visibleTrackCounter++;
    }
  });
};

const handleTrackFileChange = (event: Event, trackIndex: number) => {
  const target = event.target as HTMLInputElement;
  const track = releaseFormData.tracks[trackIndex];
  if (target.files && target.files[0] && track) {
    track._audioFileObject = target.files[0];
    track.audio_file = target.files[0].name; // Display new file name
  } else if (track) {
    track._audioFileObject = null;
    // If clearing file for an existing track, backend might need explicit null
  }
};
const handleCoverArtChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const fileType = target.files[0].type;
    if (fileType === "image/gif") {
      alert(
        "Animated GIFs are not allowed for cover art. Please choose a JPG or PNG."
      );
      target.value = "";
      releaseFormData.new_cover_art_file = null;
      // Do not revert cover_art_url here, let user see what they selected before error
      return;
    }
    releaseFormData.new_cover_art_file = target.files[0];
    releaseFormData.cover_art_url = URL.createObjectURL(target.files[0]); // Preview new cover
  } else {
    releaseFormData.new_cover_art_file = null;
    // Optionally revert to original cover_art_url if user clears selection,
    // but this might require fetching original data again or storing it separately.
    // For now, if cleared, no new file is sent.
  }
};

const handleSubmit = async () => {
  if (!releaseFormData.id) {
    error.value = "Cannot update: Release ID is missing.";
    return;
  }
  if (!fullReleaseDateTime.value) {
    error.value = "Invalid release date or time specified.";
    isLoading.value = false;
    return;
  }

  isSubmitting.value = true;
  error.value = null;

  // Step 1: Update Release Details
  const releaseUpdatePayload = new FormData();
  releaseUpdatePayload.append("title", releaseFormData.title);
  releaseUpdatePayload.append("release_type", releaseFormData.release_type);
  releaseUpdatePayload.append("release_date", fullReleaseDateTime.value);
  releaseUpdatePayload.append(
    "is_published",
    releaseFormData.is_published.toString()
  );

  if (releaseFormData.new_cover_art_file) {
    releaseUpdatePayload.append(
      "cover_art",
      releaseFormData.new_cover_art_file
    );
  } else if (
    releaseFormData.new_cover_art_file === null &&
    releaseFormData.cover_art_url === null
  ) {
    // If user explicitly wants to remove cover art (logic for this needs UI, e.g. a "Remove Cover" button)
    // For now, sending empty string might be a convention for clearing.
    // releaseUpdatePayload.append("cover_art", ""); // Backend needs to handle empty string to clear
  }

  releaseFormData.genre_names.forEach((name) =>
    releaseUpdatePayload.append("genre_names", name)
  );

  try {
    await axios.patch(
      `/releases/${releaseFormData.id}/`,
      releaseUpdatePayload,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );

    // Step 2: Process Tracks (Create, Update, Delete)
    for (let i = 0; i < releaseFormData.tracks.length; i++) {
      const track = releaseFormData.tracks[i];

      if (track._isRemoved && track._originalId) {
        // Delete existing track
        await axios.delete(`/tracks/${track._originalId}/`);
      } else if (!track._isRemoved) {
        const trackNumberToSubmit = track.track_number; // Use the current track_number from form
        if (trackNumberToSubmit === null || trackNumberToSubmit <= 0) {
          console.warn(
            `Skipping track ${
              track.title || "Untitled"
            } due to invalid track number.`
          );
          continue;
        }

        if (track._isNew) {
          // Create new track
          if (!track.title || !track._audioFileObject) continue;
          const newTrackPayload = new FormData();
          newTrackPayload.append("title", track.title);
          newTrackPayload.append("audio_file", track._audioFileObject);
          newTrackPayload.append("release", releaseFormData.id.toString());
          newTrackPayload.append(
            "track_number",
            trackNumberToSubmit.toString()
          );
          track.genre_names.forEach((name) =>
            newTrackPayload.append("genre_names", name)
          );

          await axios.post("/tracks/", newTrackPayload); // Will trigger Track.save()
        } else if (track._originalId) {
          // Update existing track
          const updateTrackPayload = new FormData();
          updateTrackPayload.append("title", track.title);
          updateTrackPayload.append(
            "track_number",
            trackNumberToSubmit.toString()
          ); // Send track number
          if (track._audioFileObject) {
            // If a new audio file was selected
            updateTrackPayload.append("audio_file", track._audioFileObject);
          }
          track.genre_names.forEach((name) =>
            updateTrackPayload.append("genre_names", name)
          );

          await axios.patch(
            `/tracks/${track._originalId}/`,
            updateTrackPayload,
            {
              headers: { "Content-Type": "multipart/form-data" },
            }
          ); // Will trigger Track.save()
        }
      }
    }
    alert("Release updated successfully!");
    router.push({ name: "release-detail", params: { id: releaseFormData.id } });
  } catch (err: any) {
    console.error("Failed to update release or tracks:", err);
    if (axios.isAxiosError(err) && err.response) {
      const errors = err.response.data;
      let detailedError = "";
      if (typeof errors === "object" && errors !== null) {
        detailedError = Object.entries(errors)
          .map(
            ([field, messages]) =>
              `${field}: ${
                Array.isArray(messages) ? messages.join(", ") : messages
              }`
          )
          .join(" | ");
      }
      error.value = `Error (${err.response.status}): ${
        detailedError || "Failed to update."
      }`;
      if (
        err.response.data.cover_art &&
        Array.isArray(err.response.data.cover_art)
      ) {
        if (
          err.response.data.cover_art.some((e: string) => e.includes("GIF"))
        ) {
          error.value += " GIFs are not allowed for cover art.";
        }
      }
    } else {
      error.value = "An unexpected error occurred during update.";
    }
  } finally {
    // Only set isSubmitting to false if there was an error,
    // otherwise navigation will occur. If navigation is blocked by error, then set to false.
    if (error.value) isSubmitting.value = false;
  }
};

// Watch for route param changes to refetch if navigating between edit pages (less common)
watch(
  () => route.params.id,
  (newId) => {
    if (newId && newId !== releaseFormData.id?.toString()) {
      fetchGenres();
      fetchReleaseData(newId as string);
    }
  }
);
</script>

<template>
  <div class="edit-release-page">
    <h2>Edit Release</h2>
    <div v-if="isLoading" class="loading-message">Loading release data...</div>
    <div
      v-else-if="error && !releaseFormData.id"
      class="error-message initial-load-error"
    >
      {{ error }}
    </div>
    <form
      v-else-if="releaseFormData.id"
      @submit.prevent="handleSubmit"
      class="release-form"
    >
      <fieldset>
        <legend>Release Information</legend>
        <div class="form-group">
          <label for="release-title-edit">Title:</label>
          <input
            type="text"
            id="release-title-edit"
            v-model="releaseFormData.title"
            required
          />
        </div>
        <div class="form-group">
          <label for="release-type-edit">Type:</label>
          <select id="release-type-edit" v-model="releaseFormData.release_type">
            <option value="ALBUM">Album</option>
            <option value="EP">EP</option>
            <option value="SINGLE">Single</option>
          </select>
        </div>
        <div class="form-group form-group-datetime">
          <div>
            <label for="release-date-edit">Release Date:</label>
            <input
              type="date"
              id="release-date-edit"
              v-model="releaseFormData.release_date_str"
              required
            />
          </div>
          <div>
            <label for="release-time-edit">Release Time (UTC):</label>
            <input
              type="time"
              id="release-time-edit"
              v-model="releaseFormData.release_time_str"
            />
          </div>
        </div>
        <div class="form-group">
          <label for="cover-art-edit">Cover Art (JPG/PNG only):</label>
          <img
            v-if="releaseFormData.cover_art_url"
            :src="releaseFormData.cover_art_url"
            alt="Current Cover Art"
            class="current-cover"
          />
          <p v-else>(No current cover art)</p>
          <input
            type="file"
            id="cover-art-edit"
            @change="handleCoverArtChange"
            accept="image/jpeg,image/png,image/webp"
          />
        </div>
        <div class="form-group">
          <label for="release-genres-edit">Release Genres:</label>
          <div class="genre-chips">
            <span
              v-for="(genre, index) in releaseFormData.genre_names"
              :key="`release-genre-edit-${index}`"
              class="chip"
            >
              {{ genre }}
              <button
                type="button"
                @click="removeReleaseGenreChip(index)"
                class="chip-remove"
              >
                ×
              </button>
            </span>
          </div>
          <input
            type="text"
            v-model="newReleaseGenre"
            @keydown.enter.prevent="addReleaseGenreChip"
            placeholder="Type genre and press Enter"
            class="genre-input"
            list="existing-genres-datalist-edit"
          />
          <datalist id="existing-genres-datalist-edit">
            <option
              v-for="g in availableGenres"
              :key="`datalist-edit-${g.id}`"
              :value="g.name"
            ></option>
          </datalist>
          <button
            type="button"
            @click="addReleaseGenreChip"
            class="add-genre-button"
          >
            Add Genre
          </button>
        </div>
        <div class="form-group form-group-checkbox">
          <input
            type="checkbox"
            id="is-published-edit"
            v-model="releaseFormData.is_published"
          />
          <label for="is-published-edit"
            >Is Published? (Uncheck for Draft)</label
          >
        </div>
      </fieldset>
      <fieldset>
        <legend>Tracks</legend>
        <div
          v-for="(track, index) in releaseFormData.tracks"
          :key="track.id"
          class="track-entry"
          :class="{ 'marked-for-removal': track._isRemoved }"
        >
          <div v-if="!track._isRemoved">
            <h4>
              Track {{ track.track_number || index + 1 }}
              <span v-if="track._isNew" class="new-badge">(New)</span>
              <span v-else-if="track._originalId" class="id-badge"
                >(ID: {{ track._originalId }})</span
              >
            </h4>
            <div class="form-group">
              <label :for="`track-number-edit-${track.id}`">Track #:</label>
              <input
                type="number"
                :id="`track-number-edit-${track.id}`"
                v-model.number="track.track_number"
                min="1"
                placeholder="No."
                class="track-number-input"
              />
            </div>
            <div class="form-group">
              <label :for="`track-title-edit-${track.id}`">Track Title:</label>
              <input
                type="text"
                :id="`track-title-edit-${track.id}`"
                v-model="track.title"
                required
              />
            </div>
            <div class="form-group">
              <label :for="`track-file-edit-${track.id}`">Audio File:</label>
              <span
                v-if="
                  track.audio_file && !track._audioFileObject && !track._isNew
                "
                class="current-file-name"
              >
                Current:
                {{
                  typeof track.audio_file === "string"
                    ? track.audio_file.substring(
                        track.audio_file.lastIndexOf("/") + 1
                      )
                    : "File present"
                }}
              </span>
              <span v-if="track._audioFileObject" class="current-file-name"
                >New: {{ track._audioFileObject.name }}</span
              >
              <input
                type="file"
                :id="`track-file-edit-${track.id}`"
                @change="handleTrackFileChange($event, index)"
                accept="audio/*"
              />
            </div>
            <div class="form-group">
              <label :for="`track-genres-input-edit-${track.id}`"
                >Track Genres:</label
              >
              <div class="genre-chips">
                <span
                  v-for="(genreName, gIndex) in track.genre_names"
                  :key="`track-edit-${track.id}-genre-${gIndex}`"
                  class="chip"
                >
                  {{ genreName }}
                  <button
                    type="button"
                    @click="removeTrackGenreChip(index, gIndex)"
                    class="chip-remove"
                  >
                    ×
                  </button>
                </span>
              </div>
              <input
                type="text"
                v-model="newTrackGenres[index]"
                @keydown.enter.prevent="addTrackGenreChip(index)"
                placeholder="Type genre and press Enter"
                class="genre-input"
                :list="`existing-genres-datalist-track-edit-${track.id}`"
              />
              <datalist :id="`existing-genres-datalist-track-edit-${track.id}`">
                <option
                  v-for="g in availableGenres"
                  :key="`datalist-track-edit-${track.id}-${g.id}`"
                  :value="g.name"
                ></option>
              </datalist>
              <button
                type="button"
                @click="addTrackGenreChip(index)"
                class="add-genre-button"
              >
                Add Genre
              </button>
            </div>
            <button
              type="button"
              @click="markTrackForRemoval(index)"
              class="remove-track-button"
            >
              Remove Track
            </button>
          </div>
          <div v-else class="removed-track-indicator">
            <p>
              Track "{{ track.title || "New Track" }}" (Original ID:
              {{ track._originalId || "N/A" }}) will be removed upon saving.
            </p>
            <button
              type="button"
              @click="unmarkTrackForRemoval(index)"
              class="undo-remove-button"
            >
              Undo Remove
            </button>
          </div>
        </div>
        <button type="button" @click="addTrack" class="add-track-button">
          Add New Track
        </button>
      </fieldset>
      <div
        v-if="error && !isLoading && releaseFormData.id"
        class="error-message backend-error"
      >
        {{ error }}
      </div>
      <div class="form-actions">
        <button type="submit" :disabled="isSubmitting || isLoading">
          {{ isSubmitting ? "Saving..." : "Save Changes" }}
        </button>
        <button
          type="button"
          @click="router.go(-1)"
          :disabled="isSubmitting || isLoading"
          class="cancel-button"
        >
          Cancel
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.edit-release-page {
  max-width: 800px;
  margin: 2rem auto;
  padding: 1.5rem;
}
.release-form fieldset {
  border: 1px solid var(--color-border);
  padding: 1.5rem;
  margin-bottom: 2rem;
  border-radius: 8px;
}
.release-form legend {
  font-size: 1.2em;
  font-weight: bold;
  padding: 0 0.5em;
}
.form-group {
  margin-bottom: 1rem;
  text-align: left;
}
.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 500;
}
.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="date"],
.form-group input[type="time"],
.form-group input[type="file"],
.form-group select,
.form-group .genre-input {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1em;
}
.track-number-input {
  width: 80px !important;
  text-align: center;
}
.form-group-datetime {
  display: flex;
  gap: 1rem;
}
.form-group-datetime > div {
  flex: 1;
}
.form-group-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.form-group-checkbox input[type="checkbox"] {
  width: auto;
  margin-right: 0.5em;
}
.form-group-checkbox label {
  margin-bottom: 0;
  font-weight: normal;
}
.genre-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}
.chip {
  background-color: var(--color-background-mute);
  padding: 0.3em 0.7em;
  border-radius: 16px;
  font-size: 0.9em;
  display: flex;
  align-items: center;
}
.chip-remove {
  background: none;
  border: none;
  color: var(--color-text);
  margin-left: 0.5em;
  cursor: pointer;
  font-size: 1.1em;
  padding: 0;
  line-height: 1;
}
.chip-remove:hover {
  color: red;
}
.genre-input {
  margin-top: 0.5rem;
}
.add-genre-button {
  margin-left: 0.5rem;
  padding: 0.4rem 0.6rem;
  font-size: 0.9em;
  vertical-align: baseline;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
.track-entry {
  border: 1px dashed var(--color-border);
  padding: 1rem;
  margin-bottom: 1.5rem;
  border-radius: 6px;
  background-color: var(--color-background-soft);
}
.track-entry.marked-for-removal {
  opacity: 0.6;
  border-style: solid;
  border-color: red;
  background-color: #4d323260;
}
.removed-track-indicator {
  padding: 1rem;
  text-align: center;
  color: #ffc0c0;
}
.undo-remove-button {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  padding: 0.3em 0.8em;
  font-size: 0.9em;
  margin-top: 0.5em;
}
.track-entry h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--color-heading);
}
.new-badge,
.id-badge {
  font-size: 0.8em;
  color: var(--color-text-light);
  font-weight: normal;
  margin-left: 0.5em;
}
.current-cover {
  max-width: 150px;
  max-height: 150px;
  display: block;
  margin-bottom: 0.5rem;
  border-radius: 4px;
}
.current-file-name {
  display: block;
  font-size: 0.85em;
  color: var(--color-text-light);
  margin-bottom: 0.3em;
  font-style: italic;
}
.remove-track-button,
.add-track-button {
  padding: 0.5em 1em;
  font-size: 0.9em;
  margin-top: 0.5em;
  border-radius: 4px;
}
.remove-track-button {
  background-color: #693030;
  color: white;
  border: 1px solid #8a4040;
}
.remove-track-button:hover {
  background-color: #8a4040;
}
.add-track-button {
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
}
.add-track-button:hover {
  border-color: var(--color-border-hover);
}
.error-message {
  color: red;
  margin-bottom: 1rem;
  padding: 0.7rem;
  border: 1px solid red;
  border-radius: 4px;
  background-color: #ffdddd1c;
  text-align: left;
}
.loading-message,
.initial-load-error {
  padding: 2rem;
  text-align: center;
  font-style: italic;
}
.backend-error {
  margin-top: 1rem;
}
.form-actions {
  margin-top: 2rem;
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}
.form-actions button {
  padding: 0.7rem 1.5rem;
}
.cancel-button {
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
}
.cancel-button:hover {
  border-color: var(--color-border-hover);
}
</style>
