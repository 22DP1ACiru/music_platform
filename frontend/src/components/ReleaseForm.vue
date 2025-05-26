<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch, type PropType } from "vue";
import axios from "axios";

// --- Interfaces ---
export interface TrackFormData {
  id: number | string;
  title: string;
  track_number: number | null;
  audio_file_url?: string | null;
  audio_file_object?: File | null;
  genre_names: string[];
  _isNew?: boolean;
  _isRemoved?: boolean;
  _originalId?: number;
}

export interface ReleaseFormData {
  id?: number | null;
  title: string;
  release_type: "ALBUM" | "EP" | "SINGLE";
  release_date_str: string;
  release_time_str: string;
  cover_art_url?: string | null;
  new_cover_art_file?: File | null;
  genre_names: string[];
  is_published: boolean;
  tracks: TrackFormData[];

  // New shop fields
  download_file_url?: string | null; // URL for existing download file
  new_download_file_object?: File | null; // New download file
  pricing_model: "FREE" | "PAID" | "NYP";
  price?: number | string | null; // string for input, number for API
  currency?: string | null;
  minimum_price_nyp?: number | string | null; // string for input, number for API
}

interface Genre {
  id: number;
  name: string;
}

// --- Props ---
const props = defineProps({
  initialData: {
    type: Object as PropType<Partial<ReleaseFormData>>,
    default: () => ({}),
  },
  isEditMode: {
    type: Boolean,
    default: false,
  },
  isLoadingSubmit: {
    type: Boolean,
    default: false,
  },
});

// --- Emits ---
const emit = defineEmits<{
  (
    e: "submit-release",
    formData: ReleaseFormData & { release_date_for_api: string | null }
  ): void;
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
  new_cover_art_file: props.initialData?.new_cover_art_file || null,
  genre_names: [...(props.initialData?.genre_names || [])],
  is_published:
    props.initialData?.is_published === undefined
      ? true
      : props.initialData.is_published,
  tracks: props.initialData?.tracks?.map((t) => ({ ...t })) || [],

  // Initialize new shop fields
  download_file_url: props.initialData?.download_file_url || null,
  new_download_file_object: props.initialData?.new_download_file_object || null,
  pricing_model: props.initialData?.pricing_model || "PAID", // Default to PAID
  price:
    props.initialData?.price === undefined ? null : props.initialData.price, // Allow null, handle empty string from input
  currency: props.initialData?.currency || "USD",
  minimum_price_nyp:
    props.initialData?.minimum_price_nyp === undefined
      ? null
      : props.initialData.minimum_price_nyp,
});

const availableGenres = ref<Genre[]>([]);
const newReleaseGenreInput = ref("");
const newTrackGenreInputs = ref<string[]>([]);

const localTrackIdCounter = ref(Date.now());

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
    id: `new-${localTrackIdCounter.value++}`,
    title: "",
    track_number: newTrackNumber,
    audio_file_url: null,
    audio_file_object: null,
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
    track.audio_file_url = target.files[0].name;
  } else if (track) {
    track.audio_file_object = null;
  }
};

const handleCoverArtChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const fileType = target.files[0].type;
    if (fileType === "image/gif") {
      alert("Animated GIFs are not allowed. Please use a JPG, PNG, or WEBP.");
      target.value = "";
      formState.new_cover_art_file = null;
      if (props.isEditMode && props.initialData?.cover_art_url) {
        formState.cover_art_url = props.initialData.cover_art_url;
      } else if (
        !props.isEditMode &&
        formState.cover_art_url &&
        formState.cover_art_url.startsWith("blob:")
      ) {
        URL.revokeObjectURL(formState.cover_art_url);
        formState.cover_art_url = null;
      }
      return;
    }
    formState.new_cover_art_file = target.files[0];
    if (
      formState.cover_art_url &&
      formState.cover_art_url.startsWith("blob:")
    ) {
      URL.revokeObjectURL(formState.cover_art_url);
    }
    formState.cover_art_url = URL.createObjectURL(target.files[0]);
  } else {
    formState.new_cover_art_file = null;
    if (
      formState.cover_art_url &&
      formState.cover_art_url.startsWith("blob:")
    ) {
      URL.revokeObjectURL(formState.cover_art_url);
    }
    if (props.isEditMode && props.initialData?.cover_art_url) {
      formState.cover_art_url = props.initialData.cover_art_url;
    } else {
      formState.cover_art_url = null;
    }
  }
};

const handleDownloadFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    formState.new_download_file_object = target.files[0];
    formState.download_file_url = URL.createObjectURL(target.files[0]); // Preview for new file
  } else {
    formState.new_download_file_object = null;
    // Revert to original if edit mode and clearing selection
    if (props.isEditMode && props.initialData?.download_file_url) {
      formState.download_file_url = props.initialData.download_file_url;
    } else {
      formState.download_file_url = null;
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
  if (
    formState.pricing_model === "PAID" &&
    (formState.price === null ||
      formState.price === "" ||
      Number(formState.price) < 0)
  ) {
    alert("Price is required and cannot be negative for 'Paid' model.");
    return;
  }
  if (formState.pricing_model === "PAID" && !formState.currency) {
    alert("Currency is required for 'Paid' model.");
    return;
  }
  if (
    formState.pricing_model === "NYP" &&
    formState.minimum_price_nyp !== null &&
    formState.minimum_price_nyp !== "" &&
    Number(formState.minimum_price_nyp) < 0
  ) {
    alert("Minimum 'Name Your Price' cannot be negative.");
    return;
  }
  if (
    !formState.new_download_file_object &&
    !formState.download_file_url &&
    props.isEditMode
  ) {
    // In edit mode, if there's no existing download file and no new one, it's okay if they intend to clear it.
    // Or, if creating, and no download file provided. This could be allowed if pricing is FREE.
  } else if (
    !formState.new_download_file_object &&
    !formState.download_file_url &&
    !props.isEditMode
  ) {
    // if creating and no download file, it implies it's not downloadable yet, unless it's free.
    // The backend model requires pricing_model regardless.
    // Let's assume for now a download file is generally expected if not FREE.
    if (formState.pricing_model !== "FREE") {
      // alert("A download file is required unless the pricing model is 'Free'.");
      // return;
      // This rule can be very strict. Let backend validate if file is truly mandatory.
    }
  }

  const dataToEmit = {
    ...formState,
    new_cover_art_file:
      formState.new_cover_art_file instanceof File
        ? formState.new_cover_art_file
        : null,
    // Pass the download file object
    new_download_file_object:
      formState.new_download_file_object instanceof File
        ? formState.new_download_file_object
        : null,
    tracks: formState.tracks.map((track) => ({
      ...track,
      audio_file_object:
        track.audio_file_object instanceof File
          ? track.audio_file_object
          : null,
    })),
    release_date_for_api: apiDate,
    // Convert price strings to numbers or null
    price:
      formState.price === "" || formState.price === null
        ? null
        : Number(formState.price),
    minimum_price_nyp:
      formState.minimum_price_nyp === "" || formState.minimum_price_nyp === null
        ? null
        : Number(formState.minimum_price_nyp),
  };

  emit("submit-release", dataToEmit);
};

const cancel = () => {
  emit("cancel-form");
};

// --- Lifecycle Hooks & Watchers ---
onMounted(() => {
  fetchGenres();
  if (formState.tracks.length === 0 && !props.isEditMode) {
    addTrack();
  }
  if (props.initialData?.tracks) {
    newTrackGenreInputs.value = props.initialData.tracks.map(() => "");
  }
});

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
    formState.new_cover_art_file = newData?.new_cover_art_file || null;
    formState.genre_names = [...(newData?.genre_names || [])];
    formState.is_published =
      newData?.is_published === undefined ? true : newData.is_published;

    formState.tracks =
      newData?.tracks?.map((t) => ({
        ...t,
        _isNew: t._isNew === undefined ? false : t._isNew,
        audio_file_object:
          t.audio_file_object instanceof File ? t.audio_file_object : null,
      })) || [];

    // Initialize new shop fields from props
    formState.download_file_url = newData?.download_file_url || null;
    formState.new_download_file_object =
      newData?.new_download_file_object || null;
    formState.pricing_model = newData?.pricing_model || "PAID";
    formState.price = newData?.price === undefined ? null : newData.price;
    formState.currency = newData?.currency || "USD";
    formState.minimum_price_nyp =
      newData?.minimum_price_nyp === undefined
        ? null
        : newData.minimum_price_nyp;

    newTrackGenreInputs.value = formState.tracks.map(() => "");
    if (formState.tracks.length === 0 && !props.isEditMode) {
      addTrack();
    }
  },
  { deep: true, immediate: true }
);

watch(
  () => formState.pricing_model,
  (newModel) => {
    if (newModel !== "PAID") {
      formState.price = null;
      // formState.currency = null; // Or keep default USD? Let's keep default for now.
    }
    if (newModel !== "NYP") {
      formState.minimum_price_nyp = null;
    }
  }
);
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

    <!-- Download and Pricing Section -->
    <fieldset>
      <legend>Download & Pricing</legend>
      <div class="form-group">
        <label for="download-file-form">Download File (e.g., ZIP):</label>
        <div class="download-file-preview-container">
          <span
            v-if="
              formState.download_file_url && !formState.new_download_file_object
            "
          >
            Current:
            {{
              formState.download_file_url.substring(
                formState.download_file_url.lastIndexOf("/") + 1
              )
            }}
          </span>
          <span v-else-if="formState.new_download_file_object">
            New: {{ formState.new_download_file_object.name }}
          </span>
          <span v-else class="placeholder">No download file selected.</span>
        </div>
        <input
          type="file"
          id="download-file-form"
          @change="handleDownloadFileChange"
        />
      </div>

      <div class="form-group">
        <label for="pricing-model-form">Pricing Model:</label>
        <select id="pricing-model-form" v-model="formState.pricing_model">
          <option value="FREE">Free</option>
          <option value="PAID">Paid (Fixed Price)</option>
          <option value="NYP">Name Your Price</option>
        </select>
      </div>

      <div
        v-if="formState.pricing_model === 'PAID'"
        class="conditional-pricing-fields"
      >
        <div class="form-group">
          <label for="price-form">Price:</label>
          <input
            type="number"
            id="price-form"
            v-model.number="formState.price"
            step="0.01"
            min="0"
            placeholder="e.g., 9.99"
          />
        </div>
        <div class="form-group">
          <label for="currency-form">Currency:</label>
          <select id="currency-form" v-model="formState.currency">
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="GBP">GBP</option>
            <!-- Add more currencies as needed from shop.models.CURRENCY_CHOICES -->
          </select>
        </div>
      </div>

      <div
        v-if="formState.pricing_model === 'NYP'"
        class="conditional-pricing-fields"
      >
        <div class="form-group">
          <label for="minimum-price-nyp-form"
            >Minimum Price (optional, 0 for no minimum):</label
          >
          <input
            type="number"
            id="minimum-price-nyp-form"
            v-model.number="formState.minimum_price_nyp"
            step="0.01"
            min="0"
            placeholder="e.g., 1.00"
          />
        </div>
        <div class="form-group">
          <!-- NYP also needs a currency for transactions -->
          <label for="nyp-currency-form">Currency for NYP Transactions:</label>
          <select id="nyp-currency-form" v-model="formState.currency">
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="GBP">GBP</option>
          </select>
        </div>
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
  width: 100%;
  height: auto;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  display: block;
}
.cover-art-preview.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-background-mute);
  color: var(--color-text-light);
  font-style: italic;
  width: 200px;
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
.download-file-preview-container {
  font-size: 0.9em;
  font-style: italic;
  color: var(--color-text-light);
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  background-color: var(--color-background-mute);
  border-radius: 4px;
  min-height: 1.5em; /* Ensure it has some height even if empty */
}
.download-file-preview-container .placeholder {
  color: var(--color-text);
}
.conditional-pricing-fields {
  padding-left: 1rem;
  border-left: 2px solid var(--color-border);
  margin-top: 1rem;
  padding-top: 0.5rem;
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
