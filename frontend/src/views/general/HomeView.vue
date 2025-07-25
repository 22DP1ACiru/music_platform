<script setup lang="ts">
import { ref, onMounted } from "vue";
import axios from "axios";
import HighlightsCarousel from "@/components/home/HighlightsCarousel.vue";
import ReleaseCardSmall from "@/components/release/ReleaseCardSmall.vue";
import type { CarouselSlide, HighlightItem, ReleaseSummary } from "@/types";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const carouselItems = ref<CarouselSlide[]>([]);
const latestReleases = ref<ReleaseSummary[]>([]);
const popularReleases = ref<ReleaseSummary[]>([]);

const isLoadingHighlights = ref(true);
const isLoadingReleases = ref(true);
const isLoadingPopular = ref(true);

const errorHighlights = ref<string | null>(null);
const errorReleases = ref<string | null>(null);
const errorPopular = ref<string | null>(null);

async function fetchHighlights() {
  isLoadingHighlights.value = true;
  errorHighlights.value = null;
  try {
    const response = await axios.get<PaginatedResponse<HighlightItem>>(
      "/highlights/"
    );
    const activeHighlights = response.data.results;

    carouselItems.value = activeHighlights.map((item) => {
      const isReleaseHighlight = !!item.release; // True if release ID exists
      const slideType = isReleaseHighlight ? "release" : "generic";

      let displayTitle = item.effective_title; // Already good (uses custom title or release title)
      let displaySubtitle = item.subtitle; // Use custom subtitle first
      let displayDescription = item.description;
      let displayImageUrl = item.effective_image_url; // Already good (uses custom image or release cover)
      let displayLinkUrl = item.link_url;

      if (isReleaseHighlight) {
        // For release highlights, if custom fields are empty, fall back to release data
        if (!displaySubtitle)
          displaySubtitle = item.release_artist_name || undefined; // Artist name as subtitle
        // effective_title already handles fallback to release.title
        // effective_image_url already handles fallback to release.cover_art
        if (!displayLinkUrl) displayLinkUrl = `/releases/${item.release}`;
      } else {
        // For generic highlights, if custom fields are empty, we might want defaults or ensure they are set
        // The backend model's clean() method now requires title, image, and link_url for generic highlights
        // So, these fields should ideally be present in `item`.
      }

      return {
        type: slideType,
        id: `highlight-${item.id}`,
        title: displayTitle,
        subtitle: displaySubtitle || undefined, // Ensure it's undefined if truly no subtitle
        imageUrl: displayImageUrl,
        description: displayDescription || undefined,
        linkUrl: displayLinkUrl || undefined, // Ensure it's undefined if no link
      };
    });

    if (carouselItems.value.length === 0) {
      // This fallback might still be useful if the API returns zero results
      // and you always want at least one slide.
      carouselItems.value.push({
        type: "generic",
        id: "welcome-slide-default",
        title: "Welcome to Vaultwave!",
        subtitle: "A humble new beginning for music lovers...",
        imageUrl: null,
        description:
          "Soon there will be featured highlights here, showcasing the best of our music releases and artists. Stay tuned!",
        linkUrl: "/about",
      });
    }
  } catch (err) {
    console.error("HomeView: Failed to fetch highlights:", err);
    errorHighlights.value = "Could not load featured highlights.";
    carouselItems.value = [
      {
        type: "generic",
        id: "error-slide",
        title: "Error Loading Highlights",
        description: "Please try again later.",
        linkUrl: "/",
        imageUrl: null,
      },
    ];
  } finally {
    isLoadingHighlights.value = false;
  }
}

async function fetchLatestReleases() {
  isLoadingReleases.value = true;
  errorReleases.value = null;
  try {
    const response = await axios.get<PaginatedResponse<ReleaseSummary>>(
      "/releases/?limit=6&ordering=-release_date"
    );
    latestReleases.value = response.data.results;
  } catch (err) {
    console.error("HomeView: Failed to fetch latest releases:", err);
    errorReleases.value = "Could not load latest releases.";
  } finally {
    isLoadingReleases.value = false;
  }
}

async function fetchPopularReleases() {
  isLoadingPopular.value = true;
  errorPopular.value = null;
  try {
    const response = await axios.get<PaginatedResponse<ReleaseSummary>>(
      "/releases/?limit=6&ordering=-listen_count"
    );
    popularReleases.value = response.data.results.filter(
      (r) => (r.listen_count || 0) > 0
    );
  } catch (err) {
    console.error("HomeView: Failed to fetch popular releases:", err);
    errorPopular.value = "Could not load popular releases at this time.";
  } finally {
    isLoadingPopular.value = false;
  }
}

onMounted(() => {
  fetchHighlights();
  fetchLatestReleases();
  fetchPopularReleases();
});
</script>

<template>
  <div class="home-view">
    <section class="highlights-section">
      <div
        v-if="isLoadingHighlights && carouselItems.length === 0"
        class="loading-placeholder"
      >
        Loading Highlights...
      </div>
      <div
        v-else-if="errorHighlights && carouselItems.length === 0"
        class="error-message"
      >
        {{ errorHighlights }}
      </div>
      <HighlightsCarousel v-else :items="carouselItems" />
    </section>

    <section class="latest-releases-section">
      <h2>Latest Releases</h2>
      <div v-if="isLoadingReleases" class="loading-placeholder">
        Loading Latest Releases...
      </div>
      <div v-else-if="errorReleases" class="error-message">
        {{ errorReleases }}
      </div>
      <div v-else-if="latestReleases.length === 0" class="empty-message">
        No new releases at the moment. Check back soon!
      </div>
      <div v-else class="releases-grid">
        <ReleaseCardSmall
          v-for="release in latestReleases"
          :key="`latest-${release.id}`"
          :release="release"
        />
      </div>
    </section>

    <section class="popular-releases-section">
      <h2>Popular Releases</h2>
      <div v-if="isLoadingPopular" class="loading-placeholder">
        Loading Popular Releases...
      </div>
      <div v-else-if="errorPopular" class="error-message">
        {{ errorPopular }}
      </div>
      <div v-else-if="popularReleases.length === 0" class="empty-message">
        Nothing is popular yet! Start listening to some tracks.
      </div>
      <div v-else class="releases-grid">
        <ReleaseCardSmall
          v-for="release in popularReleases"
          :key="`popular-${release.id}`"
          :release="release"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  gap: 3rem;
}

.highlights-section {
  margin-bottom: 2rem;
}

.latest-releases-section h2,
.popular-releases-section h2 {
  font-size: 1.8em;
  color: var(--color-heading);
  margin-bottom: 1.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.releases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1.5rem;
}

.loading-placeholder,
.empty-message,
.placeholder-message {
  text-align: center;
  padding: 2rem;
  font-style: italic;
  color: var(--color-text-light);
  background-color: var(--color-background-soft);
  border-radius: 6px;
}

.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
}
</style>
