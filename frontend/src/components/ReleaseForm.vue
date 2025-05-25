<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch, type PropType } from "vue";
import axios from "axios";

// --- Interfaces ---
export interface TrackFormData {
  id: number | string; // Can be temp string/number for new, number for existing
  title: string;
  track_number: number | null;
  audio_file_url?: string | null; // URL for existing audio
  audio_file_object?: File | null; // New audio file object
  genre_names: string[];
  _isNew?: boolean;
  _isRemoved?: boolean;
  _originalId?: number; // DB ID for existing tracks
}

export interface ReleaseFormData {
  id?: number | null; // Only for edit mode
  title: string;
  release_type: "ALBUM" | "EP" | "SINGLE";
  release_date_str: string; // YYYY-MM-DD
  release_time_str: string; // HH:MM
  cover_art_url?: string | null; // URL for existing cover art
  new_cover_art_file?: File | null; // New cover art file object
  genre_names: string[];
  is_published: boolean;
  tracks: TrackFormData[];
}

interface Genre {
  id: number;
  name: string;
}

// --- Props ---
const props = defineProps({
  initialData: {
    type: Object as PropType<Partial<ReleaseFormData>>, // Partial because create mode won't have all fields
    default: () => ({}),
  },
  isEditMode: {
    type: Boolean,
    default: false,
  },
  isLoadingSubmit: {
    // To show loading state from parent
    type: Boolean,
    default: false,
  },
});

// --- Emits ---
const emit = defineEmits<{
  (
    e: "submit-release",
    formData: ReleaseFormData & { release_date_for_api: string | null }
  ): void; // Add API date to emitted type
  (e: "cancel-form"): void;
}>();

// --- Reactive State ---
const formState = reactive<ReleaseFormData>({
  id: props.initialData?.id || undefined,
  title: props.initialData?.title || "",
  release_type: props.initialData?.release_type || "ALBUM",
  release_date_str:
    props.initialData?.release_date_str ||
    new Date().toISOString().split("T")[0],
  release_time_str:
    props.initialData?.release_time_str ||
    (() => {
      const now = new Date();
      return `${now.getHours().toString().padStart(2, "0")}:${now
        .getMinutes()
        .toString()
        .padStart(2, "0")}`;
    })(),
  cover_art_url: props.initialData?.cover_art_url || null,
  new_cover_art_file: props.initialData?.new_cover_art_file || null, // Will be a File object if provided
  genre_names: [...(props.initialData?.genre_names || [])],
  is_published:
    props.initialData?.is_published === undefined
      ? true
      : props.initialData.is_published,
  tracks: props.initialData?.tracks?.map((t) => ({ ...t })) || [],
});

const availableGenres = ref<Genre[]>([]);
const newReleaseGenreInput = ref(""); // For new genre input for the release
const newTrackGenreInputs = ref<string[]>([]); // For new genre inputs for each track

const localTrackIdCounter = ref(Date.now()); // For unique keys for new tracks in v-for

// --- Computed Properties ---
const fullReleaseDateTimeForSubmission = computed(() => {
  if (formState.release_date_str && formState.release_time_str) {
    const localDateTime = new Date(
      `${formState.release_date_str}T${formState.release_time_str}`
    );
    return isNaN(localDateTime.getTime()) ? null : localDateTime.toISOString();
  }
  if (formState.release_date_str) {
    const localDate = new Date(formState.release_date_str + "T00:00:00");
    return isNaN(localDate.getTime()) ? null : localDate.toISOString();
  }
  return null;
});

// --- Methods ---
const fetchGenres = async () => {
  try {
    const response = await axios.get<Genre[]>("/genres/");
    availableGenres.value = response.data;
    newTrackGenreInputs.value = formState.tracks.map(() => "");
  } catch (err) {
    console.error("ReleaseForm: Failed to fetch genres:", err);
    // Potentially emit an error or show a message
  }
};

const addReleaseGenreChip = () => {
  const genreToAdd = newReleaseGenreInput.value.trim();
  if (genreToAdd && !formState.genre_names.includes(genreToAdd)) {
    formState.genre_names.push(genreToAdd);
  }
  newReleaseGenreInput.value = "";
};
const removeReleaseGenreChip = (index: number) => {
  formState.genre_names.splice(index, 1);
};

const addTrackGenreChip = (trackIndex: number) => {
  const genreToAdd = newTrackGenreInputs.value[trackIndex]?.trim();
  if (
    genreToAdd &&
    !formState.tracks[trackIndex].genre_names.includes(genreToAdd)
  ) {
    formState.tracks[trackIndex].genre_names.push(genreToAdd);
  }
  if (newTrackGenreInputs.value[trackIndex] !== undefined) {
    newTrackGenreInputs.value[trackIndex] = "";
  }
};
const removeTrackGenreChip = (trackIndex: number, genreChipIndex: number) => {
  formState.tracks[trackIndex]?.genre_names.splice(genreChipIndex, 1);
};

const addTrack = () => {
  const newTrackNumber =
    formState.tracks.filter((t) => !t._isRemoved).length + 1;
  formState.tracks.push({
    id: `new-${localTrackIdCounter.value++}`, // Temporary frontend ID
    title: "",
    track_number: newTrackNumber,
    audio_file_url: null, // for new tracks
    audio_file_object: null, // for new tracks
    genre_names: [],
    _isNew: true,
    _isRemoved: false,
  });
  newTrackGenreInputs.value.push("");
};

const removeOrMarkTrack = (index: number) => {
  const track = formState.tracks[index];
  if (track) {
    if (track._isNew) {
      formState.tracks.splice(index, 1);
      newTrackGenreInputs.value.splice(index, 1);
    } else {
      track._isRemoved = true;
    }
    updateTrackNumbers();
  }
};
const unmarkTrackForRemoval = (index: number) => {
  const track = formState.tracks[index];
  if (track && !track._isNew) {
    track._isRemoved = false;
    updateTrackNumbers();
  }
};

const updateTrackNumbers = () => {
  let visibleTrackCounter = 1;
  formState.tracks.forEach((t) => {
    if (!t._isRemoved) {
      t.track_number = visibleTrackCounter++;
    }
  });
};

const handleTrackFileChange = (event: Event, trackIndex: number) => {
  const target = event.target as HTMLInputElement;
  const track = formState.tracks[trackIndex];
  if (target.files && target.files[0] && track) {
    track.audio_file_object = target.files[0];
    track.audio_file_url = target.files[0].name; // Display new file name as placeholder
  } else if (track) {
    track.audio_file_object = null;
    // If clearing a new file for an existing track, we might want to revert audio_file_url to original
    // This depends on how complex we want the "undo" of file selection to be.
    // For now, clearing it just means no new file is selected. The existing file (if any) remains on backend unless a new one is uploaded.
  }
};

const handleCoverArtChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const fileType = target.files[0].type;
    if (fileType === "image/gif") {
      alert("Animated GIFs are not allowed. Please use a JPG, PNG, or WEBP.");
      target.value = ""; // Clear the input
      formState.new_cover_art_file = null;
      // Revert preview if it was changed to the GIF
      if (props.isEditMode && props.initialData?.cover_art_url) {
        formState.cover_art_url = props.initialData.cover_art_url;
      } else if (
        !props.isEditMode &&
        formState.cover_art_url &&
        formState.cover_art_url.startsWith("blob:")
      ) {
        URL.revokeObjectURL(formState.cover_art_url); // Clean up blob URL
        formState.cover_art_url = null;
      }
      return;
    }
    formState.new_cover_art_file = target.files[0]; // This is a File object
    if (
      formState.cover_art_url &&
      formState.cover_art_url.startsWith("blob:")
    ) {
      URL.revokeObjectURL(formState.cover_art_url); // Clean up previous blob URL if any
    }
    formState.cover_art_url = URL.createObjectURL(target.files[0]); // Preview new
  } else {
    formState.new_cover_art_file = null;
    // If user clears selection, revert to original URL if in edit mode
    if (
      formState.cover_art_url &&
      formState.cover_art_url.startsWith("blob:")
    ) {
      URL.revokeObjectURL(formState.cover_art_url); // Clean up blob URL
    }
    if (props.isEditMode && props.initialData?.cover_art_url) {
      formState.cover_art_url = props.initialData.cover_art_url;
    } else {
      // Create mode or edit mode where original was null
      formState.cover_art_url = null;
    }
  }
};

const triggerSubmit = () => {
  if (!formState.title.trim()) {
    alert("Release title is required.");
    return;
  }
  const apiDate = fullReleaseDateTimeForSubmission.value;
  if (!apiDate) {
    alert("Invalid release date or time.");
    return;
  }

  // Create a new object for submission to ensure reactivity doesn't interfere
  // and to explicitly pass File objects.
  const dataToEmit = {
    ...formState, // Spreads all properties from formState
    // Ensure File objects are passed directly, not their reactive proxies if any confusion
    new_cover_art_file:
      formState.new_cover_art_file instanceof File
        ? formState.new_cover_art_file
        : null,
    tracks: formState.tracks.map((track) => ({
      ...track,
      audio_file_object:
        track.audio_file_object instanceof File
          ? track.audio_file_object
          : null,
    })),
    release_date_for_api: apiDate,
  };

  emit("submit-release", dataToEmit);
};

const cancel = () => {
  emit("cancel-form"); // Parent view will handle navigation
};

// --- Lifecycle Hooks & Watchers ---
onMounted(() => {
  fetchGenres();
  if (formState.tracks.length === 0 && !props.isEditMode) {
    addTrack();
  }
  // Sync newTrackGenreInputs length if initialData for tracks exists
  if (props.initialData?.tracks) {
    newTrackGenreInputs.value = props.initialData.tracks.map(() => "");
  }
});

// Watch for changes in initialData if the form needs to be reset from parent
watch(
  () => props.initialData,
  (newData) => {
    formState.id = newData?.id || undefined;
    formState.title = newData?.title || "";
    formState.release_type = newData?.release_type || "ALBUM";
    formState.release_date_str =
      newData?.release_date_str || new Date().toISOString().split("T")[0];
    formState.release_time_str =
      newData?.release_time_str ||
      (() => {
        const now = new Date();
        return `${now.getHours().toString().padStart(2, "0")}:${now
          .getMinutes()
          .toString()
          .padStart(2, "0")}`;
      })();
    formState.cover_art_url = newData?.cover_art_url || null;
    formState.new_cover_art_file = newData?.new_cover_art_file || null; // Should be File or null
    formState.genre_names = [...(newData?.genre_names || [])];
    formState.is_published =
      newData?.is_published === undefined ? true : newData.is_published;

    // Ensure tracks are properly mapped, preserving File objects if they exist in initialData
    formState.tracks =
      newData?.tracks?.map((t) => ({
        ...t,
        _isNew: t._isNew === undefined ? false : t._isNew,
        audio_file_object:
          t.audio_file_object instanceof File ? t.audio_file_object : null, // Preserve File object
      })) || [];

    newTrackGenreInputs.value = formState.tracks.map(() => "");
    if (formState.tracks.length === 0 && !props.isEditMode) {
      addTrack();
    }
  },
  { deep: true, immediate: true }
); // immediate: true to run on initial props too
</script>

<template>
  <form @submit.prevent="triggerSubmit" class="release-form-component">
    <fieldset>
      <legend>Release Information</legend>
      <div class="form-group">
        <label for="release-title-form">Title:</label>
        <input
          type="text"
          id="release-title-form"
          v-model="formState.title"
          required
        />
      </div>
      <div class="form-group">
        <label for="release-type-form">Type:</label>
        <select id="release-type-form" v-model="formState.release_type">
          <option value="ALBUM">Album</option>
          <option value="EP">EP</option>
          <option value="SINGLE">Single</option>
        </select>
      </div>
      <div class="form-group form-group-datetime">
        <div>
          <label for="release-date-form">Release Date:</label>
          <input
            type="date"
            id="release-date-form"
            v-model="formState.release_date_str"
            required
          />
        </div>
        <div>
          <label for="release-time-form">Release Time (Local):</label>
          <input
            type="time"
            id="release-time-form"
            v-model="formState.release_time_str"
          />
        </div>
      </div>
      <div class="form-group">
        <label for="cover-art-form">Cover Art (JPG/PNG/WEBP only):</label>
        <div class="cover-art-preview-container">
          <img
            v-if="formState.cover_art_url"
            :src="formState.cover_art_url"
            alt="Cover Art Preview"
            class="cover-art-preview"
          />
          <div v-else class="cover-art-preview placeholder">
            No Cover Selected
          </div>
        </div>
        <input
          type="file"
          id="cover-art-form"
          @change="handleCoverArtChange"
          accept="image/jpeg,image/png,image/webp"
        />
      </div>
      <div class="form-group">
        <label for="release-genres-form">Release Genres:</label>
        <div class="genre-chips">
          <span
            v-for="(genre, index) in formState.genre_names"
            :key="`release-genre-form-${index}`"
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
          v-model="newReleaseGenreInput"
          @keydown.enter.prevent="addReleaseGenreChip"
          placeholder="Type genre and press Enter"
          class="genre-input"
          list="existing-genres-datalist-form"
        />
        <datalist id="existing-genres-datalist-form">
          <option
            v-for="g in availableGenres"
            :key="`datalist-form-${g.id}`"
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
          id="is-published-form"
          v-model="formState.is_published"
        />
        <label for="is-published-form">Publish now? (Uncheck for Draft)</label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Tracks</legend>
      <div
        v-for="(track, index) in formState.tracks"
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
            <label :for="`track-number-form-${track.id}`">Track #:</label>
            <input
              type="number"
              :id="`track-number-form-${track.id}`"
              v-model.number="track.track_number"
              min="1"
              placeholder="No."
              class="track-number-input"
            />
          </div>
          <div class="form-group">
            <label :for="`track-title-form-${track.id}`">Track Title:</label>
            <input
              type="text"
              :id="`track-title-form-${track.id}`"
              v-model="track.title"
              required
            />
          </div>
          <div class="form-group">
            <label :for="`track-file-form-${track.id}`">Audio File:</label>
            <span
              v-if="
                track.audio_file_url &&
                !track.audio_file_object &&
                !track._isNew
              "
              class="current-file-name"
            >
              Current:
              {{
                typeof track.audio_file_url === "string"
                  ? track.audio_file_url.substring(
                      track.audio_file_url.lastIndexOf("/") + 1
                    )
                  : "File present"
              }}
            </span>
            <span v-if="track.audio_file_object" class="current-file-name"
              >New: {{ track.audio_file_object.name }}</span
            >
            <input
              type="file"
              :id="`track-file-form-${track.id}`"
              @change="handleTrackFileChange($event, index)"
              accept="audio/*"
              :required="track._isNew && !track.audio_file_object"
            />
          </div>
          <div class="form-group">
            <label :for="`track-genres-input-form-${track.id}`"
              >Track Genres:</label
            >
            <div class="genre-chips">
              <span
                v-for="(genreName, gIndex) in track.genre_names"
                :key="`track-form-${track.id}-genre-${gIndex}`"
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
              v-model="newTrackGenreInputs[index]"
              @keydown.enter.prevent="addTrackGenreChip(index)"
              placeholder="Type genre and press Enter"
              class="genre-input"
              :list="`existing-genres-datalist-track-form-${track.id}`"
            />
            <datalist :id="`existing-genres-datalist-track-form-${track.id}`">
              <option
                v-for="g in availableGenres"
                :key="`datalist-track-form-${track.id}-${g.id}`"
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
            @click="removeOrMarkTrack(index)"
            class="remove-track-button"
          >
            {{ track._isNew ? "Remove New Track" : "Mark for Removal" }}
          </button>
        </div>
        <div v-else class="removed-track-indicator">
          <p>
            Track "{{ track.title || "New Track" }}" (Original ID:
            {{ track._originalId || "N/A" }}) will be removed.
          </p>
          <button
            type="button"
            @click="unmarkTrackForRemoval(index)"
            class="undo-remove-button"
          >
            Undo
          </button>
        </div>
      </div>
      <button type="button" @click="addTrack" class="add-track-button">
        Add Track
      </button>
    </fieldset>

    <div class="form-actions">
      <button type="submit" :disabled="isLoadingSubmit">
        {{
          isLoadingSubmit
            ? "Saving..."
            : isEditMode
            ? "Save Changes"
            : "Create Release"
        }}
      </button>
      <button
        type="button"
        @click="cancel"
        :disabled="isLoadingSubmit"
        class="cancel-button"
      >
        Cancel
      </button>
    </div>
  </form>
</template>

<style scoped>
.release-form-component {
  max-width: 800px;
  margin: 0 auto; /* Form itself might not need margin if parent view handles it */
}
.release-form-component fieldset {
  border: 1px solid var(--color-border);
  padding: 1.5rem;
  margin-bottom: 2rem;
  border-radius: 8px;
}
.release-form-component legend {
  font-size: 1.2em;
  font-weight: bold;
  padding: 0 0.5em;
  color: var(--color-heading);
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

.cover-art-preview-container {
  margin-bottom: 0.5rem;
}
.cover-art-preview {
  max-width: 200px;
  max-height: 200px;
  width: 100%; /* Make it responsive within its container */
  height: auto; /* Maintain aspect ratio */
  aspect-ratio: 1 / 1; /* Enforce square aspect ratio */
  object-fit: cover; /* Crop image to fit */
  border: 1px solid var(--color-border);
  border-radius: 4px;
  display: block; /* Remove extra space below image */
}
.cover-art-preview.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-background-mute);
  color: var(--color-text-light);
  font-style: italic;
  width: 200px; /* Fixed size for placeholder */
  height: 200px;
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
