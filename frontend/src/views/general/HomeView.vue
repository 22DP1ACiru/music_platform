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
const isLoadingHighlights = ref(true);
const isLoadingReleases = ref(true);
const errorHighlights = ref<string | null>(null);
const errorReleases = ref<string | null>(null);

const welcomeSlide: CarouselSlide = {
  type: "welcome",
  id: "welcome-slide",
  title: "Welcome to Vaultwave!",
  subtitle: "Your New Home for Music Discovery & Commerce",
  imageUrl: null, // Or a generic welcome image URL
  description:
    "Explore unique releases, support artists directly, and build your digital music collection. Vaultwave connects fans with the music they love.",
  // linkUrl: '/about' // Optional link for the welcome slide
};

async function fetchHighlights() {
  isLoadingHighlights.value = true;
  errorHighlights.value = null;
  try {
    const response = await axios.get<PaginatedResponse<HighlightItem>>(
      "/highlights/"
    );
    const activeHighlights = response.data.results.filter(
      (h) => h.is_active && h.release.is_published // Ensure highlight is active and release is published
    );

    const highlightSlides: CarouselSlide[] = activeHighlights.map((item) => ({
      type: "release",
      id: `highlight-${item.id}`,
      title: item.release.title,
      subtitle: item.release.artist.name,
      imageUrl: item.release.cover_art,
      linkUrl: `/releases/${item.release.id}`,
      releaseObject: item.release,
    }));

    carouselItems.value = [welcomeSlide, ...highlightSlides];
  } catch (err) {
    console.error("HomeView: Failed to fetch highlights:", err);
    errorHighlights.value = "Could not load featured highlights.";
    carouselItems.value = [welcomeSlide]; // Show welcome slide even if highlights fail
  } finally {
    isLoadingHighlights.value = false;
  }
}

async function fetchLatestReleases() {
  isLoadingReleases.value = true;
  errorReleases.value = null;
  try {
    // Assuming /api/releases/ is already ordered by latest
    const response = await axios.get<PaginatedResponse<ReleaseSummary>>(
      "/releases/?limit=12" // Fetch, for example, the latest 12 releases
    );
    latestReleases.value = response.data.results;
  } catch (err) {
    console.error("HomeView: Failed to fetch latest releases:", err);
    errorReleases.value = "Could not load latest releases.";
  } finally {
    isLoadingReleases.value = false;
  }
}

onMounted(() => {
  fetchHighlights();
  fetchLatestReleases();
});
</script>

<template>
  <div class="home-view">
    <section class="highlights-section">
      <div
        v-if="isLoadingHighlights && carouselItems.length <= 1"
        class="loading-placeholder"
      >
        Loading Highlights...
      </div>
      <div
        v-else-if="errorHighlights && carouselItems.length <= 1"
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
          :key="release.id"
          :release="release"
        />
      </div>
    </section>

    <section class="popular-releases-section">
      <h2>Popular Releases</h2>
      <div class="placeholder-message">
        <p>Listen tracking coming soon to show popular releases!</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-view {
  display: flex;
  flex-direction: column;
  gap: 3rem; /* Space between sections */
}

.highlights-section {
  margin-bottom: 2rem; /* Space below carousel */
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
