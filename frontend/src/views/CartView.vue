<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useCartStore } from "@/stores/cart";
import { useAuthStore } from "@/stores/auth";
import { useRouter, RouterLink } from "vue-router";

const cartStore = useCartStore();
const authStore = useAuthStore();
const router = useRouter();

const cart = computed(() => cartStore.cart);
const isLoading = computed(() => cartStore.isLoading);
const error = computed(() => cartStore.error);
const cartTotalPrice = computed(() => cartStore.cartTotalPrice);
const cartCurrency = computed(() => cartStore.cartCurrency);

onMounted(() => {
  if (authStore.isLoggedIn && !cartStore.cart) {
    cartStore.fetchCart();
  }
});

const handleRemoveItem = async (productId: number) => {
  if (confirm("Remove this item from your cart?")) {
    await cartStore.removeItemFromCart(productId);
  }
};

const handleClearCart = async () => {
  if (confirm("Are you sure you want to clear your entire cart?")) {
    await cartStore.clearCart();
  }
};

const formatPrice = (amount: string | number, currency: string) => {
  const numericAmount =
    typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(numericAmount)) return String(amount); // fallback
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency,
  }).format(numericAmount);
};

const proceedToCheckout = () => {
  if (cart.value && cart.value.items.length > 0) {
    const orderItemsPayload = cart.value.items.map((item) => ({
      product_id: item.product.id,
      quantity: 1, // Assuming quantity is always 1 for digital goods in cart
      price_override: item.price_override || undefined, // Send if NYP
    }));

    // This should eventually post to an order creation endpoint that takes cart items
    // For now, we will just simulate adding to the order store by using the existing order mechanism.
    // This is a placeholder for real checkout logic.
    console.log("Proceeding to checkout with items:", orderItemsPayload);
    // Typically, you'd post this `orderItemsPayload` to your /shop/orders/ endpoint.
    // The backend OrderCreateSerializer should be able to handle this.
    // After successful order creation, clear the cart.

    // Example of how you might integrate with the existing Order system:
    axios
      .post("/shop/orders/", { items: orderItemsPayload })
      .then((response) => {
        alert("Order placed successfully! Your cart has been cleared.");
        cartStore.clearCart(); // Clear the cart on frontend
        router.push({ name: "order-history" }); // Redirect to order history
      })
      .catch((err) => {
        console.error("Failed to create order from cart:", err);
        if (axios.isAxiosError(err) && err.response) {
          cartStore.error =
            err.response.data.detail || "Could not place order.";
        } else {
          cartStore.error = "An unexpected error occurred during checkout.";
        }
      });
  } else {
    alert("Your cart is empty.");
  }
};
</script>

<template>
  <div class="cart-view">
    <h2>Your Shopping Cart</h2>

    <div v-if="isLoading" class="loading-message">Loading cart...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!cart || cart.items.length === 0" class="empty-cart">
      <p>Your cart is empty.</p>
      <RouterLink :to="{ name: 'releases' }" class="action-button"
        >Browse Releases</RouterLink
      >
    </div>

    <div v-else class="cart-contents">
      <div class="cart-items-list">
        <div v-for="item in cart.items" :key="item.id" class="cart-item-card">
          <img
            :src="item.product.cover_art || '/placeholder-cover.png'"
            :alt="item.product.name"
            class="item-cover-art"
          />
          <div class="item-details">
            <h3 class="item-name">{{ item.product.name }}</h3>
            <p class="item-artist" v-if="item.product.artist_name">
              by {{ item.product.artist_name }}
            </p>
            <p class="item-price">
              Price: {{ formatPrice(item.effective_price, cart.currency) }}
              <span v-if="item.price_override" class="nyp-indicator"
                >(Your Price)</span
              >
            </p>
          </div>
          <button
            @click="handleRemoveItem(item.product.id)"
            class="remove-item-btn"
            title="Remove item"
          >
            🗑️
          </button>
        </div>
      </div>

      <div class="cart-summary">
        <h3>Cart Total: {{ formatPrice(cartTotalPrice, cartCurrency) }}</h3>
        <div class="cart-actions">
          <button @click="handleClearCart" class="action-button clear-cart-btn">
            Clear Cart
          </button>
          <button @click="proceedToCheckout" class="action-button checkout-btn">
            Proceed to Checkout
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cart-view {
  max-width: 900px;
  margin: 2rem auto;
  padding: 1rem;
}
.cart-view h2 {
  text-align: center;
  margin-bottom: 2rem;
  color: var(--color-heading);
}

.loading-message,
.empty-cart {
  text-align: center;
  padding: 2rem;
  font-style: italic;
  color: var(--color-text-light);
}
.empty-cart .action-button {
  margin-top: 1rem;
}

.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
}

.cart-contents {
  background-color: var(--color-background-soft);
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid var(--color-border);
}

.cart-items-list {
  margin-bottom: 2rem;
}

.cart-item-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 0;
  border-bottom: 1px solid var(--color-border-hover);
}
.cart-item-card:last-child {
  border-bottom: none;
}

.item-cover-art {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--color-background-mute);
  flex-shrink: 0;
}

.item-details {
  flex-grow: 1;
}
.item-name {
  font-size: 1.1em;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0 0 0.25rem 0;
}
.item-artist {
  font-size: 0.9em;
  color: var(--color-text-light);
  margin: 0 0 0.25rem 0;
}
.item-price {
  font-size: 1em;
  color: var(--color-text);
}
.nyp-indicator {
  font-size: 0.8em;
  font-style: italic;
  color: var(--color-text-light);
}

.remove-item-btn {
  background: none;
  border: 1px solid transparent;
  color: var(--vt-c-red);
  font-size: 1.2em;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 4px;
}
.remove-item-btn:hover {
  background-color: var(--vt-c-red-soft);
  border-color: var(--vt-c-red-dark);
}

.cart-summary {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 2px solid var(--color-border);
  text-align: right;
}
.cart-summary h3 {
  font-size: 1.4em;
  margin-bottom: 1rem;
  color: var(--color-heading);
}

.cart-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.action-button {
  padding: 0.7em 1.5em;
  font-size: 1em;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid transparent;
}
.clear-cart-btn {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border-color: var(--color-border);
}
.clear-cart-btn:hover {
  background-color: var(--color-border);
}
.checkout-btn {
  background-color: var(--color-accent);
  color: var(--vt-c-white);
  border-color: var(--color-accent);
}
.checkout-btn:hover {
  background-color: var(--color-accent-hover);
}
</style>
