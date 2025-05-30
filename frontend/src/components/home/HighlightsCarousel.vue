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
    default: 7000, // Auto-play interval in milliseconds
  },
});

const currentIndex = ref(0);
let autoPlayTimer: number | undefined = undefined;

const currentSlide = computed(() => {
  return props.items[currentIndex.value];
});

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
    // Ensure items are present before starting
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
        <img
          v-if="currentSlide.imageUrl"
          :src="currentSlide.imageUrl"
          :alt="currentSlide.title"
          class="slide-image"
        />
        <div v-else class="slide-image-placeholder">
          <span v-if="currentSlide.type === 'welcome'">🎶</span>
          <span v-else>🎧</span>
        </div>

        <div class="slide-content">
          <h2 class="slide-title">{{ currentSlide.title }}</h2>
          <p v-if="currentSlide.subtitle" class="slide-subtitle">
            {{ currentSlide.subtitle }}
          </p>
          <p v-if="currentSlide.description" class="slide-description">
            {{ currentSlide.description }}
          </p>
          <RouterLink
            v-if="currentSlide.linkUrl && currentSlide.type === 'release'"
            :to="currentSlide.linkUrl"
            class="slide-link"
            >View Release</RouterLink
          >
        </div>
      </div>
    </transition>

    <button
      v-if="items.length > 1"
      @click="prevSlide"
      class="carousel-control prev"
      aria-label="Previous slide"
    >
      &#10094;
    </button>
    <button
      v-if="items.length > 1"
      @click="nextSlide"
      class="carousel-control next"
      aria-label="Next slide"
    >
      &#10095;
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
  <div v-else class="carousel-empty">
    <!-- Placeholder or message when no items -->
  </div>
</template>

<style scoped>
.highlights-carousel {
  position: relative;
  width: 100%;
  min-height: 300px; /* Minimum height */
  max-height: 450px; /* Maximum height */
  overflow: hidden;
  border-radius: 8px;
  background-color: var(--color-background-mute);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  display: flex; /* Added for centering placeholder */
  align-items: center; /* Added for centering placeholder */
  justify-content: center; /* Added for centering placeholder */
}

.carousel-slide {
  width: 100%;
  height: 100%; /* Make slide take full height of carousel */
  display: flex; /* Use flex for layout */
  position: absolute; /* For transitions */
  top: 0;
  left: 0;
}

.slide-image,
.slide-image-placeholder {
  width: 50%; /* Image takes half the width */
  height: 100%; /* Image takes full height */
  object-fit: cover;
}

.slide-image-placeholder {
  background-color: var(--color-background-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 5rem; /* Adjust icon size */
  color: var(--color-text-light);
}
.slide-image-placeholder span {
  opacity: 0.5;
}

.slide-content {
  width: 50%; /* Content takes the other half */
  padding: 2rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start; /* Align text to the left */
  color: var(--color-text);
  text-align: left;
  box-sizing: border-box;
  overflow-y: auto;
}

.slide-content .slide-title {
  font-size: 2.2em;
  font-weight: bold;
  color: var(--color-heading);
  margin: 0 0 0.5rem 0;
}

.slide-content .slide-subtitle {
  font-size: 1.2em;
  color: var(--color-text);
  margin: 0 0 1rem 0;
}

.slide-content .slide-description {
  font-size: 1em;
  line-height: 1.6;
  margin: 0 0 1.5rem 0;
  color: var(--color-text-light);
}

.slide-link {
  padding: 0.6rem 1.2rem;
  background-color: var(--color-accent);
  color: white;
  text-decoration: none;
  border-radius: 4px;
  font-weight: 500;
  transition: background-color 0.2s;
}
.slide-link:hover {
  background-color: var(--color-accent-hover);
}

.carousel-control {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background-color: rgba(0, 0, 0, 0.4);
  color: white;
  border: none;
  padding: 0.8rem;
  cursor: pointer;
  font-size: 1.5rem;
  z-index: 10;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}
.carousel-control:hover {
  background-color: rgba(0, 0, 0, 0.7);
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
  gap: 0.5rem;
  z-index: 10;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: background-color 0.2s;
}
.dot.active {
  background-color: white;
}
.dot:hover {
  background-color: rgba(255, 255, 255, 0.8);
}

/* Transition for slides */
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
    min-height: 350px; /* Adjust for smaller screens */
    max-height: 500px;
  }
  .carousel-slide {
    flex-direction: column; /* Stack image and content */
  }
  .slide-image,
  .slide-image-placeholder,
  .slide-content {
    width: 100%; /* Both take full width */
  }
  .slide-image,
  .slide-image-placeholder {
    height: 55%; /* Image takes a portion of the height */
    max-height: 250px;
  }
  .slide-content {
    height: 45%; /* Content takes remaining height */
    padding: 1.5rem;
    align-items: center; /* Center content on small screens */
    text-align: center;
  }
  .slide-content .slide-title {
    font-size: 1.8em;
  }
  .slide-content .slide-subtitle {
    font-size: 1.1em;
  }
  .slide-content .slide-description {
    font-size: 0.9em;
    margin-bottom: 1rem;
  }
  .slide-link {
    align-self: center;
  }
}
</style>
