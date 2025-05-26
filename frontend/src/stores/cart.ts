// frontend/src/stores/cart.ts
import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import axios from "axios";
import type { Cart, CartItem } from "@/types";
import { useAuthStore } from "./auth";
import { useLibraryStore } from "./library";

export const useCartStore = defineStore("cart", () => {
  const cart = ref<Cart | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const authStore = useAuthStore();
  const libraryStore = useLibraryStore();

  const itemCount = computed(() => cart.value?.items.length || 0);
  const cartTotalPrice = computed(() => cart.value?.total_price || "0.00");
  const cartCurrency = computed(() => cart.value?.currency || "USD");

  async function fetchCart() {
    if (!authStore.isLoggedIn) {
      cart.value = null;
      return;
    }
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.get<Cart>("/cart/my-cart/");
      cart.value = response.data;
    } catch (err) {
      console.error("Cart Store: Failed to fetch cart:", err);
      if (axios.isAxiosError(err) && err.response?.status !== 404) {
        error.value = "Could not load your cart.";
      }
      cart.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  async function addItemToCart(
    productId: number,
    priceOverride?: number | string | null
  ) {
    if (!authStore.isLoggedIn) {
      error.value = "Please log in to add items to your cart.";
      return false;
    }

    // Check if the item is already in the cart to get its release_id for library check
    // Or, if you have a separate product detail endpoint that returns release_id, use that.
    // For now, let's assume we need to add it first (or it's not in cart), then check library.
    // A better approach would be to fetch product details separately if not already available.
    // For simplicity, this check is now less robust without Product details fetched separately.
    // To make it robust, fetch Product details here including its release_id.
    // This is a placeholder for that logic.
    // const releaseIdOfProduct = getReleaseIdForProduct(productId); // You'd implement this

    // The cart/add-item/ endpoint returns the updated cart. We can check the newly added item there.
    // This isn't ideal as it adds then potentially errors, but simpler for now.

    isLoading.value = true;
    error.value = null;
    try {
      const payload: { product_id: number; price_override?: string } = {
        product_id: productId,
      };
      if (priceOverride !== undefined && priceOverride !== null) {
        payload.price_override = parseFloat(String(priceOverride)).toFixed(2);
      }
      const response = await axios.post<Cart>("/cart/add-item/", payload);

      // After adding, check if the corresponding release is in the library.
      // This assumes the backend add_item doesn't already do this check.
      const addedCartItem = response.data.items.find(
        (item) => item.product.id === productId
      );
      if (
        addedCartItem &&
        addedCartItem.product.release_id &&
        libraryStore.getLibraryItemByReleaseId(addedCartItem.product.release_id)
      ) {
        // If it's already in library, we should probably remove it from cart and inform user.
        // This is more of a backend validation or a pre-check.
        // For now, let's allow adding but the "Buy" button logic should prevent this scenario.
        console.warn(
          "Item added to cart but corresponding release is already in library."
        );
      }

      cart.value = response.data;
      return true;
    } catch (err) {
      console.error("Cart Store: Failed to add item to cart:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value = err.response.data.detail || "Could not add item to cart.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function removeItemFromCart(productId: number) {
    if (!authStore.isLoggedIn || !cart.value) return false;
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.delete<Cart>(
        `/cart/remove-item/${productId}/`
      );
      cart.value = response.data;
      return true;
    } catch (err) {
      console.error("Cart Store: Failed to remove item from cart:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value = err.response.data.detail || "Could not remove item.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function clearCart() {
    if (!authStore.isLoggedIn || !cart.value) return false;
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post<Cart>("/cart/clear/");
      cart.value = response.data;
      return true;
    } catch (err) {
      console.error("Cart Store: Failed to clear cart:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value = err.response.data.detail || "Could not clear cart.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  watch(
    () => authStore.isLoggedIn,
    (isLoggedIn) => {
      if (isLoggedIn) {
        fetchCart();
      } else {
        cart.value = null;
      }
    },
    { immediate: true }
  );

  return {
    cart,
    isLoading,
    error,
    itemCount,
    cartTotalPrice,
    cartCurrency,
    fetchCart,
    addItemToCart,
    removeItemFromCart,
    clearCart,
  };
});
