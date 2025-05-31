<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import axios from "axios";
import HighlightForm from "@/components/admin/HighlightForm.vue";
import type { HighlightItem } from "@/types";

const props = defineProps<{
  highlightId: string;
}>();

const router = useRouter();
const route = useRoute();

const initialData = ref<Partial<HighlightItem> | null>(null);
const isLoadingData = ref(true);
const isSubmittingForm = ref(false);
const error = ref<string | null>(null);

function parseDrfError(responseData: any): string {
  if (typeof responseData === "string") {
    return responseData;
  }
  if (typeof responseData === "object" && responseData !== null) {
    if (responseData.detail && typeof responseData.detail === "string") {
      return responseData.detail;
    }

    const keys = Object.keys(responseData);
    if (keys.length === 1) {
      const key = keys[0];
      const errorsForKey = responseData[key];
      if (
        Array.isArray(errorsForKey) &&
        errorsForKey.length === 1 &&
        typeof errorsForKey[0] === "string"
      ) {
        // If a specific field error, and it's the only one, return its message directly
        // Or prefix with field name: return `${key.charAt(0).toUpperCase() + key.slice(1)}: ${errorsForKey[0]}`;
        return errorsForKey[0];
      }
    }

    const fieldErrors: string[] = [];
    for (const key of keys) {
      const errorsForKey = responseData[key];
      if (Array.isArray(errorsForKey)) {
        fieldErrors.push(
          `${key.charAt(0).toUpperCase() + key.slice(1)}: ${errorsForKey.join(
            ", "
          )}`
        );
      } else if (typeof errorsForKey === "string") {
        fieldErrors.push(
          `${key.charAt(0).toUpperCase() + key.slice(1)}: ${errorsForKey}`
        );
      }
    }
    if (fieldErrors.length > 0) {
      return fieldErrors.join(" | ");
    }
  }
  return "An error occurred. Please check the details and try again.";
}

async function fetchHighlightForEdit(id: string) {
  isLoadingData.value = true;
  error.value = null;
  try {
    const response = await axios.get<HighlightItem>(`/highlights/${id}/`);
    initialData.value = {
      ...response.data,
      release: response.data.release,
    };
  } catch (err) {
    console.error(
      `AdminHighlightEditView: Failed to fetch highlight ${id}:`,
      err
    );
    error.value = "Could not load highlight data for editing.";
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      error.value = "Highlight not found.";
    }
  } finally {
    isLoadingData.value = false;
  }
}

const handleUpdateHighlight = async (formData: FormData) => {
  if (!initialData.value?.id) return;
  isSubmittingForm.value = true;
  error.value = null;
  try {
    await axios.patch(`/highlights/${initialData.value.id}/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    alert("Highlight updated successfully!");
    router.push({ name: "admin-highlights" });
  } catch (err: any) {
    console.error("AdminHighlightEditView: Failed to update highlight:", err);
    if (axios.isAxiosError(err) && err.response && err.response.data) {
      error.value = parseDrfError(err.response.data);
    } else if (axios.isAxiosError(err) && err.message) {
      error.value = `Network Error: ${err.message}`;
    } else {
      error.value = "An unexpected error occurred during update.";
    }
  } finally {
    isSubmittingForm.value = false;
  }
};

const handleCancel = () => {
  router.push({ name: "admin-highlights" });
};

onMounted(() => {
  fetchHighlightForEdit(props.highlightId);
});

watch(
  () => props.highlightId,
  (newId) => {
    if (newId) {
      fetchHighlightForEdit(newId);
    }
  }
);
</script>

<template>
  <div class="admin-highlight-edit-view">
    <h3>Edit Highlight</h3>
    <div v-if="isLoadingData" class="loading-message">
      Loading highlight data...
    </div>
    <div v-else-if="error && !initialData" class="error-message">
      {{ error }}
    </div>

    <HighlightForm
      v-if="initialData && !isLoadingData"
      :initial-data="initialData"
      :is-edit-mode="true"
      :is-loading-submit="isSubmittingForm"
      @submit-highlight="handleUpdateHighlight"
      @cancel-form="handleCancel"
    />
    <div v-if="error && initialData" class="error-message form-submit-error">
      {{ error }}
    </div>
  </div>
</template>

<style scoped>
.admin-highlight-edit-view {
  padding: 1rem;
  background-color: var(--color-background-soft);
  border-radius: 6px;
}
.admin-highlight-edit-view h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}
.loading-message {
  padding: 2rem;
  text-align: center;
  font-style: italic;
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}
.form-submit-error {
  margin-top: 1rem; /* Specific margin for submit errors after the form */
}
</style>
