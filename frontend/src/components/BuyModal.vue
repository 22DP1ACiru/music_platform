<script setup lang="ts">
import { type PropType, ref, computed, watch } from "vue";
import type { ReleaseDetail } from "@/types";
import { useCartStore } from "@/stores/cart";
import { useRouter } from "vue-router";
import { Decimal } from "decimal.js"; // For precise decimal arithmetic

const props = defineProps({
  release: {
    type: Object as PropType<ReleaseDetail | null>,
    required: true,
  },
  isVisible: {
    type: Boolean,
    required: true,
  },
});

const emit = defineEmits(["close", "item-added-to-cart", "error-adding-item"]);

const cartStore = useCartStore();
const router = useRouter();

const nypAmountInput = ref<string>("0.00");
const isLoadingAction = ref(false);
const localError = ref<string | null>(null);

const minNypAmount = computed(() => {
  if (
    props.release?.pricing_model === "NYP" &&
    props.release.minimum_price_nyp
  ) {
    return new Decimal(props.release.minimum_price_nyp);
  }
  return new Decimal("0.00");
});

const releasePrice = computed(() => {
  if (props.release?.pricing_model === "PAID" && props.release.price) {
    return new Decimal(props.release.price);
  }
  return null;
});

const currencySymbol = computed(() => {
  const currency = props.release?.currency;
  if (currency === "EUR") return "€";
  if (currency === "GBP") return "£";
  return "$"; // Default USD
});

watch(
  () => props.release,
  (newRelease) => {
    if (newRelease?.pricing_model === "NYP") {
      nypAmountInput.value = minNypAmount.value.toFixed(2);
    } else if (newRelease?.pricing_model === "PAID" && newRelease.price) {
      nypAmountInput.value = new Decimal(newRelease.price).toFixed(2); // Pre-fill for PAID (though not editable)
    } else {
      nypAmountInput.value = "0.00";
    }
    localError.value = null;
  },
  { immediate: true }
);

const validateNypAmount = (): boolean => {
  if (props.release?.pricing_model !== "NYP") return true; // Not applicable

  try {
    const enteredAmount = new Decimal(nypAmountInput.value);
    if (enteredAmount.isNaN() || enteredAmount.isNegative()) {
      localError.value = "Please enter a valid positive amount.";
      return false;
    }
    if (enteredAmount.lessThan(minNypAmount.value)) {
      localError.value = `The amount must be at least ${
        currencySymbol.value
      }${minNypAmount.value.toFixed(2)}.`;
      return false;
    }
    localError.value = null;
    return true;
  } catch (e) {
    localError.value = "Invalid amount entered.";
    return false;
  }
};

const handleAddToCart = async () => {
  if (!props.release || !props.release.product_info_id) {
    localError.value = "Product information is missing for this release.";
    return;
  }
  if (props.release.pricing_model === "NYP" && !validateNypAmount()) {
    return;
  }

  isLoadingAction.value = true;
  localError.value = null;

  const priceOverride =
    props.release.pricing_model === "NYP" ? nypAmountInput.value : undefined;

  const success = await cartStore.addItemToCart(
    props.release.product_info_id,
    priceOverride
  );
  if (success) {
    emit("item-added-to-cart");
    emit("close"); // Close modal on success
  } else {
    localError.value = cartStore.error || "Failed to add item to cart.";
    emit("error-adding-item", localError.value);
  }
  isLoadingAction.value = false;
};

const handleCheckoutNow = async () => {
  if (!props.release || !props.release.product_info_id) {
    localError.value = "Product information is missing for this release.";
    return;
  }
  if (props.release.pricing_model === "NYP" && !validateNypAmount()) {
    return;
  }

  isLoadingAction.value = true;
  localError.value = null;
  const priceOverride =
    props.release.pricing_model === "NYP" ? nypAmountInput.value : undefined;

  const addedToCart = await cartStore.addItemToCart(
    props.release.product_info_id,
    priceOverride
  );
  if (addedToCart) {
    emit("item-added-to-cart"); // Emit even if navigating away
    emit("close");
    router.push({ name: "cart" });
  } else {
    localError.value = cartStore.error || "Failed to add item for checkout.";
    emit("error-adding-item", localError.value);
  }
  isLoadingAction.value = false;
};

// Close modal if escape key is pressed
const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === "Escape" && props.isVisible) {
    emit("close");
  }
};

// Add/remove event listener
watch(
  () => props.isVisible,
  (newValue) => {
    if (newValue) {
      document.addEventListener("keydown", handleKeydown);
    } else {
      document.removeEventListener("keydown", handleKeydown);
    }
  }
);

// Ensure listener is removed when component is unmounted
import { onUnmounted } from "vue";
onUnmounted(() => {
  document.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <div
    v-if="isVisible && release"
    class="modal-overlay"
    @click.self="$emit('close')"
  >
    <div class="modal-content" @click.stop>
      <button class="close-button" @click="$emit('close')" title="Close modal">
        &times;
      </button>
      <h3 class="modal-title">Acquire: {{ release.title }}</h3>
      <p class="modal-artist">by {{ release.artist.name }}</p>

      <div class="modal-body">
        <div v-if="release.pricing_model === 'PAID'" class="price-display">
          <p>
            Price:
            <strong
              >{{ currencySymbol }}{{ releasePrice?.toFixed(2) }}
              {{ release.currency }}</strong
            >
          </p>
          <p>
            This item will be added to your library upon successful acquisition.
          </p>
        </div>

        <div v-if="release.pricing_model === 'NYP'" class="nyp-section">
          <label :for="`nyp-amount-modal-${release.id}`" class="nyp-label">
            Enter your price (minimum {{ currencySymbol
            }}{{ minNypAmount.toFixed(2) }} {{ release.currency }}):
          </label>
          <div class="nyp-input-wrapper">
            <span class="currency-prefix">{{ currencySymbol }}</span>
            <input
              type="number"
              :id="`nyp-amount-modal-${release.id}`"
              v-model="nypAmountInput"
              step="0.01"
              :min="minNypAmount.toFixed(2)"
              class="nyp-input-field"
              placeholder="Your price"
            />
          </div>
        </div>

        <p v-if="localError" class="error-message modal-error">
          {{ localError }}
        </p>
      </div>

      <div class="modal-actions">
        <button
          @click="handleAddToCart"
          class="action-button add-to-cart-btn"
          :disabled="isLoadingAction"
        >
          {{ isLoadingAction ? "Processing..." : "Add to Cart" }}
        </button>
        <button
          @click="handleCheckoutNow"
          class="action-button checkout-now-btn"
          :disabled="isLoadingAction"
        >
          {{ isLoadingAction ? "Processing..." : "Checkout Now" }}
        </button>
        <button
          @click="$emit('close')"
          class="action-button cancel-btn"
          :disabled="isLoadingAction"
        >
          Cancel
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050; /* Ensure it's above other content */
}

.modal-content {
  background-color: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 500px;
  position: relative;
  color: var(--color-text);
}

.close-button {
  position: absolute;
  top: 0.75rem;
  right: 1rem;
  background: none;
  border: none;
  font-size: 2rem;
  color: var(--color-text-light);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.close-button:hover {
  color: var(--color-text);
}

.modal-title {
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-size: 1.5em;
  color: var(--color-heading);
}

.modal-artist {
  font-size: 1em;
  color: var(--color-text-light);
  margin-bottom: 1.5rem;
}

.modal-body {
  margin-bottom: 1.5rem;
}

.price-display p {
  margin: 0.5rem 0;
  font-size: 1.1em;
}
.price-display strong {
  color: var(--color-accent);
}

.nyp-section {
  margin-top: 1rem;
}
.nyp-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.95em;
}
.nyp-input-wrapper {
  display: flex;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 0 0.5rem;
  background-color: var(--color-background);
}
.currency-prefix {
  padding-right: 0.3rem;
  font-size: 1.1em;
  color: var(--color-text-light);
}
.nyp-input-field {
  width: 100%;
  padding: 0.6rem 0.2rem;
  border: none;
  background-color: transparent;
  color: var(--color-text);
  font-size: 1.1em;
  outline: none;
}
/* Hide spinners on number input */
.nyp-input-field::-webkit-outer-spin-button,
.nyp-input-field::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
.nyp-input-field[type="number"] {
  -moz-appearance: textfield;
}

.error-message.modal-error {
  font-size: 0.9em;
  margin-top: 1rem;
  padding: 0.6rem;
  text-align: center;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.action-button {
  padding: 0.6em 1.2em;
  font-size: 0.95em;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid transparent;
}
.add-to-cart-btn,
.checkout-now-btn {
  background-color: var(--color-accent);
  color: var(--vt-c-white);
  border-color: var(--color-accent);
}
.add-to-cart-btn:hover,
.checkout-now-btn:hover {
  background-color: var(--color-accent-hover);
}
.add-to-cart-btn:disabled,
.checkout-now-btn:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}

.cancel-btn {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border-color: var(--color-border);
}
.cancel-btn:hover {
  border-color: var(--color-border-hover);
}
</style>
