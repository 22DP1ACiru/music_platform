<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import HighlightForm from "@/components/admin/HighlightForm.vue";

const router = useRouter();
const isLoading = ref(false);
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

const handleCreateHighlight = async (formData: FormData) => {
  isLoading.value = true;
  error.value = null;
  try {
    await axios.post("/highlights/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    alert("Highlight created successfully!");
    router.push({ name: "admin-highlights" });
  } catch (err: any) {
    console.error("AdminHighlightCreateView: Failed to create highlight:", err);
    if (axios.isAxiosError(err) && err.response && err.response.data) {
      error.value = parseDrfError(err.response.data);
    } else if (axios.isAxiosError(err) && err.message) {
      error.value = `Network Error: ${err.message}`;
    } else {
      error.value =
        "An unexpected error occurred while creating the highlight.";
    }
  } finally {
    isLoading.value = false;
  }
};

const handleCancel = () => {
  router.push({ name: "admin-highlights" });
};
</script>

<template>
  <div class="admin-highlight-create-view">
    <h3>Create New Highlight</h3>
    <div v-if="error" class="error-message">{{ error }}</div>
    <HighlightForm
      :is-edit-mode="false"
      :is-loading-submit="isLoading"
      @submit-highlight="handleCreateHighlight"
      @cancel-form="handleCancel"
    />
  </div>
</template>

<style scoped>
.admin-highlight-create-view {
  padding: 1rem;
  background-color: var(--color-background-soft);
  border-radius: 6px;
}
.admin-highlight-create-view h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}
</style>
