<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";

// --- Interfaces ---
interface TrackFormData {
  id: number; // Temporary frontend ID
  title: string;
  track_number: number | null;
  audio_file: File | null;
  genre_names: string[];
}

interface ReleaseFormData {
  title: string;
  release_type: "ALBUM" | "EP" | "SINGLE";
  release_date_str: string;
  release_time_str: string;
  cover_art: File | null;
  genre_names: string[];
  is_published: boolean;
  tracks: TrackFormData[];
}

const authStore = useAuthStore();
const router = useRouter();

const defaultTime = () => {
  const now = new Date();
  return `${now.getHours().toString().padStart(2, "0")}:${now
    .getMinutes()
    .toString()
    .padStart(2, "0")}`;
};

const releaseFormData = reactive<ReleaseFormData>({
  title: "",
  release_type: "ALBUM",
  release_date_str: new Date().toISOString().split("T")[0],
  release_time_str: defaultTime(),
  cover_art: null,
  genre_names: [],
  is_published: true,
  tracks: [],
});

const fullReleaseDateTime = computed(() => {
  if (releaseFormData.release_date_str && releaseFormData.release_time_str) {
    // Construct date in local timezone then convert to ISO string which will be UTC
    const localDateTime = new Date(
      `${releaseFormData.release_date_str}T${releaseFormData.release_time_str}`
    );
    if (isNaN(localDateTime.getTime())) {
      // Handle invalid date/time string combination
      return null;
    }
    return localDateTime.toISOString();
  }
  // Fallback if time is not provided, default to midnight UTC on that date
  if (releaseFormData.release_date_str) {
    const localDate = new Date(releaseFormData.release_date_str + "T00:00:00");
    if (isNaN(localDate.getTime())) {
      return null;
    }
    return localDate.toISOString();
  }
  return null;
});

const availableGenres = ref<{ id: number; name: string }[]>([]);
const newReleaseGenre = ref(""); // For new genre input for the release
const newTrackGenres = ref<string[]>([]); // For new genre inputs for each track, index-based

const isLoading = ref(false);
const error = ref<string | null>(null);
const trackIdCounter = ref(0); // For unique keys for new tracks in v-for

const fetchGenres = async () => {
  try {
    const response = await axios.get("/genres/");
    availableGenres.value = response.data;
    // Initialize newTrackGenres array based on initial tracks if any (though tracks start empty)
    newTrackGenres.value = releaseFormData.tracks.map(() => "");
  } catch (err) {
    console.error("Failed to fetch genres:", err);
  }
};

onMounted(() => {
  if (!authStore.hasArtistProfile) {
    error.value = "You must have an artist profile to create a release.";
    // Consider redirecting or disabling the form
    return;
  }
  fetchGenres();
  if (releaseFormData.tracks.length === 0) {
    addTrack(); // Add one initial track
  }
});

const addReleaseGenreChip = () => {
  const genreToAdd = newReleaseGenre.value.trim();
  if (genreToAdd && !releaseFormData.genre_names.includes(genreToAdd)) {
    releaseFormData.genre_names.push(genreToAdd);
  }
  newReleaseGenre.value = ""; // Clear input
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
    newTrackGenres.value[trackIndex] = ""; // Clear specific track's genre input
  }
};
const removeTrackGenreChip = (trackIndex: number, genreChipIndex: number) => {
  releaseFormData.tracks[trackIndex].genre_names.splice(genreChipIndex, 1);
};

const addTrack = () => {
  const nextTrackNumber = releaseFormData.tracks.length + 1;
  releaseFormData.tracks.push({
    id: trackIdCounter.value++,
    title: "",
    track_number: nextTrackNumber,
    audio_file: null,
    genre_names: [],
  });
  newTrackGenres.value.push(""); // Add corresponding entry for new track's genre input
};
const removeTrack = (index: number) => {
  releaseFormData.tracks.splice(index, 1);
  newTrackGenres.value.splice(index, 1); // Remove corresponding genre input state
  // Re-number subsequent tracks
  for (let i = index; i < releaseFormData.tracks.length; i++) {
    releaseFormData.tracks[i].track_number = i + 1;
  }
};
const handleTrackFileChange = (event: Event, trackIndex: number) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    releaseFormData.tracks[trackIndex].audio_file = target.files[0];
  } else {
    releaseFormData.tracks[trackIndex].audio_file = null;
  }
};

const handleCoverArtChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    // Basic client-side validation for image type (optional but good UX)
    const fileType = target.files[0].type;
    if (fileType === "image/gif") {
      alert(
        "Animated GIFs are not allowed for cover art. Please choose a JPG or PNG."
      );
      target.value = ""; // Clear the input
      releaseFormData.cover_art = null;
      return;
    }
    releaseFormData.cover_art = target.files[0];
  } else {
    releaseFormData.cover_art = null;
  }
};

const handleSubmit = async () => {
  isLoading.value = true;
  error.value = null;

  if (!authStore.hasArtistProfile) {
    error.value =
      "Artist profile could not be confirmed. Cannot create release.";
    isLoading.value = false;
    return;
  }
  if (!fullReleaseDateTime.value) {
    error.value = "Invalid release date or time specified.";
    isLoading.value = false;
    return;
  }

  const releaseApiData = new FormData();
  releaseApiData.append("title", releaseFormData.title);
  releaseApiData.append("release_type", releaseFormData.release_type);
  releaseApiData.append("release_date", fullReleaseDateTime.value); // Send ISO string
  releaseApiData.append(
    "is_published",
    releaseFormData.is_published.toString()
  );

  if (releaseFormData.cover_art) {
    releaseApiData.append("cover_art", releaseFormData.cover_art);
  }
  releaseFormData.genre_names.forEach((genre) => {
    releaseApiData.append("genre_names", genre); // DRF ListField handles this
  });

  try {
    // Step 1: Create the Release
    const releaseResponse = await axios.post("/releases/", releaseApiData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const newReleaseId = releaseResponse.data.id;

    // Step 2: Create Tracks for the Release
    for (let i = 0; i < releaseFormData.tracks.length; i++) {
      const track = releaseFormData.tracks[i];
      if (!track.title || !track.audio_file || track.track_number === null) {
        console.warn(
          `Skipping track ${i + 1} due to missing title, file, or track number.`
        );
        continue;
      }
      const trackApiData = new FormData();
      trackApiData.append("title", track.title);
      trackApiData.append("audio_file", track.audio_file);
      trackApiData.append("release", newReleaseId.toString());
      trackApiData.append("track_number", track.track_number.toString());

      track.genre_names.forEach((genre) => {
        trackApiData.append("genre_names", genre);
      });

      // This POST will trigger Track.save() on the backend for duration calculation
      await axios.post("/tracks/", trackApiData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    }
    alert("Release created successfully!");
    router.push({ name: "release-detail", params: { id: newReleaseId } });
  } catch (err: any) {
    console.error("Failed to create release or tracks:", err);
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
        detailedError || "Failed to create release."
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
      error.value = "An unexpected error occurred.";
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="create-release-page">
    <h2>Upload New Release</h2>
    <div v-if="!authStore.hasArtistProfile && !isLoading" class="error-message">
      You must have an artist profile to create a release. Please
      <RouterLink :to="{ name: 'profile' }">visit your profile</RouterLink> to
      create one.
    </div>
    <form v-else @submit.prevent="handleSubmit" class="release-form">
      <fieldset>
        <legend>Release Information</legend>
        <div class="form-group">
          <label for="release-title">Title:</label>
          <input
            type="text"
            id="release-title"
            v-model="releaseFormData.title"
            required
          />
        </div>
        <div class="form-group">
          <label for="release-type">Type:</label>
          <select id="release-type" v-model="releaseFormData.release_type">
            <option value="ALBUM">Album</option>
            <option value="EP">EP</option>
            <option value="SINGLE">Single</option>
          </select>
        </div>
        <div class="form-group form-group-datetime">
          <div>
            <label for="release-date">Release Date:</label>
            <input
              type="date"
              id="release-date"
              v-model="releaseFormData.release_date_str"
              required
            />
          </div>
          <div>
            <label for="release-time">Release Time (UTC):</label>
            <input
              type="time"
              id="release-time"
              v-model="releaseFormData.release_time_str"
            />
          </div>
        </div>
        <div class="form-group">
          <label for="cover-art">Cover Art (JPG/PNG only):</label>
          <input
            type="file"
            id="cover-art"
            @change="handleCoverArtChange"
            accept="image/jpeg,image/png,image/webp"
          />
        </div>
        <div class="form-group">
          <label for="release-genres">Release Genres:</label>
          <div class="genre-chips">
            <span
              v-for="(genre, index) in releaseFormData.genre_names"
              :key="`release-genre-${index}`"
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
            list="existing-genres-datalist"
          />
          <datalist id="existing-genres-datalist">
            <option
              v-for="genre in availableGenres"
              :key="`datalist-${genre.id}`"
              :value="genre.name"
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
            id="is-published"
            v-model="releaseFormData.is_published"
          />
          <label for="is-published"
            >Publish immediately? (Uncheck for Draft)</label
          >
        </div>
      </fieldset>
      <fieldset>
        <legend>Tracks</legend>
        <div
          v-for="(track, index) in releaseFormData.tracks"
          :key="track.id"
          class="track-entry"
        >
          <h4>Track {{ index + 1 }}</h4>
          <div class="form-group">
            <label :for="`track-number-${track.id}`">Track #:</label>
            <input
              type="number"
              :id="`track-number-${track.id}`"
              v-model.number="track.track_number"
              min="1"
              placeholder="No."
              class="track-number-input"
            />
          </div>
          <div class="form-group">
            <label :for="`track-title-${track.id}`">Track Title:</label>
            <input
              type="text"
              :id="`track-title-${track.id}`"
              v-model="track.title"
              required
            />
          </div>
          <div class="form-group">
            <label :for="`track-file-${track.id}`">Audio File:</label>
            <input
              type="file"
              :id="`track-file-${track.id}`"
              @change="handleTrackFileChange($event, index)"
              accept="audio/*"
              required
            />
          </div>
          <div class="form-group">
            <label :for="`track-genres-input-${track.id}`">Track Genres:</label>
            <div class="genre-chips">
              <span
                v-for="(genreName, gIndex) in track.genre_names"
                :key="`track-${track.id}-genre-${gIndex}`"
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
              :list="`existing-genres-datalist-track-${track.id}`"
            />
            <datalist :id="`existing-genres-datalist-track-${track.id}`">
              <option
                v-for="genre in availableGenres"
                :key="`datalist-track-${track.id}-${genre.id}`"
                :value="genre.name"
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
            @click="removeTrack(index)"
            class="remove-track-button"
            :disabled="releaseFormData.tracks.length <= 1"
          >
            Remove Track {{ index + 1 }}
          </button>
        </div>
        <button type="button" @click="addTrack" class="add-track-button">
          Add Another Track
        </button>
      </fieldset>
      <div v-if="error" class="error-message backend-error">{{ error }}</div>
      <div class="form-actions">
        <button
          type="submit"
          :disabled="isLoading || !authStore.hasArtistProfile"
        >
          {{ isLoading ? "Creating..." : "Create Release" }}
        </button>
        <button
          type="button"
          @click="router.go(-1)"
          :disabled="isLoading"
          class="cancel-button"
        >
          Cancel
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.create-release-page {
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
  margin-bottom: 1rem; /* Consistent spacing */
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
.track-entry h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--color-heading);
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
.remove-track-button:disabled {
  background-color: #4a4a4a;
  color: #888;
  border-color: #555;
  cursor: not-allowed;
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
