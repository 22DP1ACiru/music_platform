<script setup lang="ts">
import { ref, onMounted, onUnmounted, type PropType, computed } from "vue";
import type { CarouselSlide } from "@/types";
import { RouterLink } from "vue-router";

const props = defineProps({
  items: {
    type: Array as PropType<CarouselSlide[]>,
    required: true,
  },
  autoPlayInterval: {
    type: Number,
    default: 7000,
  },
});

const currentIndex = ref(0);
let autoPlayTimer: number | undefined = undefined;

const currentSlide = computed(() => {
  return props.items[currentIndex.value];
});

const isExternalLink = (url: string | undefined | null): boolean => {
  if (!url) return false;
  return (
    url.startsWith("http://") ||
    url.startsWith("https://") ||
    url.startsWith("//")
  );
};

const nextSlide = () => {
  currentIndex.value = (currentIndex.value + 1) % props.items.length;
  resetAutoPlay();
};

const prevSlide = () => {
  currentIndex.value =
    (currentIndex.value - 1 + props.items.length) % props.items.length;
  resetAutoPlay();
};

const goToSlide = (index: number) => {
  currentIndex.value = index;
  resetAutoPlay();
};

const startAutoPlay = () => {
  if (props.autoPlayInterval > 0 && props.items.length > 1) {
    autoPlayTimer = window.setInterval(nextSlide, props.autoPlayInterval);
  }
};

const stopAutoPlay = () => {
  clearInterval(autoPlayTimer);
};

const resetAutoPlay = () => {
  stopAutoPlay();
  startAutoPlay();
};

onMounted(() => {
  if (props.items.length > 0) {
    startAutoPlay();
  }
});

onUnmounted(() => {
  stopAutoPlay();
});
</script>

<template>
  <div
    v-if="items && items.length > 0"
    class="highlights-carousel"
    @mouseenter="stopAutoPlay"
    @mouseleave="startAutoPlay"
  >
    <transition name="slide-fade" mode="out-in">
      <div :key="currentSlide.id" class="carousel-slide">
        <div class="slide-image-container">
          <img
            v-if="currentSlide.imageUrl"
            :src="currentSlide.imageUrl"
            :alt="currentSlide.title"
            class="slide-image"
          />
          <div v-else class="slide-image-placeholder">
            <span
              v-if="
                currentSlide.type === 'welcome' ||
                (currentSlide.type === 'generic' && !currentSlide.imageUrl)
              "
              >🎶</span
            >
            <span
              v-else-if="
                currentSlide.type === 'release' && !currentSlide.imageUrl
              "
              >🎧</span
            >
            <span v-else-if="!currentSlide.imageUrl">🖼️</span>
          </div>
        </div>

        <div class="slide-content">
          <h2 class="slide-title truncate-text" :style="{ '--line-clamp': 2 }">
            {{ currentSlide.title }}
          </h2>
          <p v-if="currentSlide.subtitle" class="slide-subtitle">
            {{ currentSlide.subtitle }}
          </p>
          <p v-if="currentSlide.description" class="slide-description">
            {{ currentSlide.description }}
          </p>

          <!-- Conditional rendering for internal vs external links -->
          <template v-if="currentSlide.linkUrl">
            <a
              v-if="isExternalLink(currentSlide.linkUrl)"
              :href="currentSlide.linkUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="slide-link"
            >
              {{
                currentSlide.type === "release" ? "View Release" : "Learn More"
              }}
            </a>
            <RouterLink v-else :to="currentSlide.linkUrl" class="slide-link">
              {{
                currentSlide.type === "release" ? "View Release" : "Learn More"
              }}
            </RouterLink>
          </template>
        </div>
      </div>
    </transition>

    <button
      v-if="items.length > 1"
      @click="prevSlide"
      class="carousel-control prev"
      aria-label="Previous slide"
    >
      ❮
    </button>
    <button
      v-if="items.length > 1"
      @click="nextSlide"
      class="carousel-control next"
      aria-label="Next slide"
    >
      ❯
    </button>

    <div v-if="items.length > 1" class="carousel-dots">
      <span
        v-for="(item, index) in items"
        :key="`dot-${item.id}`"
        class="dot"
        :class="{ active: index === currentIndex }"
        @click="goToSlide(index)"
        role="button"
        :aria-label="`Go to slide ${index + 1}`"
      ></span>
    </div>
  </div>
  <div v-else class="carousel-empty">No highlights to display.</div>
</template>

<style scoped>
.highlights-carousel {
  position: relative;
  width: 100%;
  min-height: 350px;
  max-height: 500px;
  overflow: hidden;
  border-radius: 8px;
  background-color: var(--color-background-mute);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.carousel-slide {
  width: 100%;
  height: 100%;
  display: flex;
  position: absolute;
  top: 0;
  left: 0;
}

.slide-image-container {
  width: 45%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.slide-image,
.slide-image-placeholder {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.slide-image-placeholder {
  background-color: var(--color-background-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4.5rem;
  color: var(--color-text-light);
}
.slide-image-placeholder span {
  opacity: 0.5;
}

.slide-content {
  width: 55%;
  padding: 1.5rem 70px 1.5rem 2rem; /* Adjusted padding: T R B L */
  display: flex;
  flex-direction: column;
  justify-content: center; /* Center content vertically in the available space */
  align-items: flex-start;
  color: var(--color-text);
  text-align: left;
  box-sizing: border-box;
  overflow: hidden;
}

.truncate-text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: var(--line-clamp);
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  /* These help with wrapping before clamping, especially for long words */
  overflow-wrap: break-word;
  word-wrap: break-word; /* Legacy */
  word-break: break-word; /* More control than break-all */
}

.slide-content .slide-title {
  font-size: 1.9em; /* Slightly reduced */
  font-weight: bold;
  color: var(--color-heading);
  margin: 0 0 0.4rem 0;
  line-height: 1.2; /* Tightened line-height slightly */
}

.slide-content .slide-subtitle {
  font-size: 1.05em;
  color: var(--color-text);
  margin: 0 0 0.6rem 0;
  line-height: 1.3;
}

.slide-content .slide-description {
  font-size: 0.9em;
  line-height: 1.45;
  margin: 0 0 1rem 0;
  color: var(--color-text-light);
}

.slide-link {
  padding: 0.6rem 1.2rem;
  background-color: var(--color-accent);
  color: white;
  text-decoration: none;
  border-radius: 5px;
  font-weight: 500;
  transition: background-color 0.2s ease-in-out, transform 0.1s ease-in-out;
  margin-top: auto;
  align-self: flex-start;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
.slide-link:hover {
  background-color: var(--color-accent-hover);
  transform: translateY(-1px);
}
.slide-link:active {
  transform: translateY(0px);
}

.carousel-control {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background-color: rgba(30, 30, 30, 0.5);
  color: white;
  border: none;
  padding: 0.8rem;
  cursor: pointer;
  font-size: 1.5rem;
  z-index: 10;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease-in-out;
}
.carousel-control:hover {
  background-color: rgba(0, 0, 0, 0.8);
}

.carousel-control.prev {
  left: 1rem;
}
.carousel-control.next {
  right: 1rem;
}

.carousel-dots {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 0.6rem;
  z-index: 10;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: background-color 0.2s ease-in-out, transform 0.2s ease-in-out;
}
.dot.active {
  background-color: white;
  transform: scale(1.1);
}
.dot:hover {
  background-color: rgba(255, 255, 255, 0.7);
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: opacity 0.8s ease;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
}

.carousel-empty {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-light);
  font-style: italic;
}

@media (max-width: 768px) {
  .highlights-carousel {
    min-height: auto;
    max-height: none;
    height: 450px;
  }
  .carousel-slide {
    flex-direction: column;
  }
  .slide-image-container,
  .slide-content {
    width: 100%;
  }
  .slide-image-container {
    height: 40%;
  }
  .slide-content {
    height: 60%;
    padding: 1rem 1.5rem;
    justify-content: center;
    gap: 0.3rem;
  }
  .slide-content .slide-title {
    font-size: 1.3em;
    margin-bottom: 0.2rem;
    line-height: 1.2;
  }
  .slide-content .slide-subtitle {
    font-size: 0.85em;
    margin-bottom: 0.3rem;
    line-height: 1.25;
  }
  .slide-content .slide-description {
    font-size: 0.8em;
    margin-bottom: 0.5rem;
    line-height: 1.35;
  }
  .slide-link {
    align-self: center;
    padding: 0.5rem 1rem;
    font-size: 0.9em;
    margin-top: 0.5rem;
  }
  .carousel-control {
    width: 36px;
    height: 36px;
    font-size: 1.2rem;
  }
  .carousel-control.prev {
    left: 0.5rem;
  }
  .carousel-control.next {
    right: 0.5rem;
  }

  .carousel-dots {
    bottom: 0.75rem;
  }
  .dot {
    width: 10px;
    height: 10px;
  }
}
</style>
