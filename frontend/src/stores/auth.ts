import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import type { Router } from "vue-router";
import { usePlayerStore } from "./player";
import type { User, UserProfileForAuth, ArtistProfileForAuth } from "@/types"; // Import User type from types/index.ts

// Interfaces moved to types/index.ts and imported

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string | null>(localStorage.getItem("accessToken"));
  const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const playerStore = usePlayerStore();

  const isLoggedIn = computed(() => !!accessToken.value && !!user.value);
  const authUser = computed(() => user.value);
  const authLoading = computed(() => isLoading.value);
  const authError = computed(() => error.value);

  const hasArtistProfile = computed(
    () => !!user.value?.profile?.artist_profile_data
  );
  const artistProfileId = computed(
    () => user.value?.profile?.artist_profile_data?.id || null
  );
  const isStaff = computed(() => !!user.value?.is_staff); // New computed for staff status

  async function fetchUser(router?: Router) {
    if (!accessToken.value) {
      user.value = null;
      return;
    }

    try {
      // UserSerializer now includes is_staff, so this fetches it
      const userResponse = await axios.get<User>("/users/me/");
      let profileData: UserProfileForAuth | null = null;
      try {
        const profileApiResponse = await axios.get<UserProfileForAuth>(
          "/profiles/me/"
        );
        profileData = profileApiResponse.data;
      } catch (profileError) {
        console.warn(
          "Auth Store: Could not fetch user profile details during fetchUser:",
          profileError
        );
        if (
          axios.isAxiosError(profileError) &&
          profileError.response?.status === 401
        ) {
          await logout(router);
          return;
        }
      }
      // Construct the user object including the fetched 'is_staff'
      user.value = {
        id: userResponse.data.id,
        username: userResponse.data.username,
        email: userResponse.data.email,
        is_staff: userResponse.data.is_staff, // Make sure this is assigned
        profile: profileData,
      };
      console.log("Auth Store: Fetched user and profile data:", user.value);
    } catch (err: any) {
      console.error("Auth Store: Failed to fetch user base data:", err);
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        await logout(router);
      } else {
        user.value = null;
      }
    }
  }

  async function login(
    payload: { username?: string; password?: string },
    router?: Router
  ) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post("/token/", payload);
      if (response.data.access && response.data.refresh) {
        localStorage.setItem("accessToken", response.data.access);
        localStorage.setItem("refreshToken", response.data.refresh);
        accessToken.value = response.data.access;
        refreshToken.value = response.data.refresh;
        await fetchUser(router);
        if (user.value && router) {
          const redirectPath =
            (router.currentRoute.value.query.redirect as string) || "/";
          router.push(redirectPath);
        } else if (!user.value) {
          error.value = "Login succeeded but failed to fetch user details.";
        }
      } else {
        throw new Error("Token data missing in login response");
      }
    } catch (err: any) {
      console.error("Auth Store: Login failed:", err);
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      accessToken.value = null;
      refreshToken.value = null;
      user.value = null;
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail || "Login failed. Check username/password.";
      } else {
        error.value = "An unexpected network error occurred during login.";
      }
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function logout(router?: Router) {
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    isLoading.value = false;
    error.value = null;

    playerStore.resetPlayerState();

    try {
      const { useCartStore } = await import("./cart");
      const cartStore = useCartStore();
      cartStore.cart = null;
    } catch (e) {
      console.error(
        "AuthStore: Error accessing/resetting cartStore during logout:",
        e
      );
    }
    try {
      const { useChatStore } = await import("./chat");
      const chatStore = useChatStore();
      chatStore.setActiveChatViewIdentity("USER"); // Reset chat view
      // Chat store should also clear its state via its own auth subscription
    } catch (e) {
      console.error(
        "AuthStore: Error accessing/resetting chatStore during logout:",
        e
      );
    }

    console.log("Auth Store: Logged Out.");
    if (router) {
      try {
        if (router.currentRoute.value.meta.requiresAuth) {
          await router.push({ name: "login" });
        } else if (router.currentRoute.value.meta.requiresStaff) {
          await router.push({ name: "home" }); // or login
        }
      } catch (navError) {
        console.error("Auth Store: Failed to redirect after logout", navError);
      }
    }
  }

  async function register(payload: any, router: Router) {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post("/register/", payload);
      console.log("Auth Store: Registration successful:", response.data);
      alert("Registration successful! Please log in.");
      router.push({ name: "login" });
    } catch (err: any) {
      console.error("Auth Store: Registration failed:", err);
      if (axios.isAxiosError(err) && err.response) {
        const errors = err.response.data;
        if (typeof errors === "object" && errors !== null) {
          error.value = Object.entries(errors)
            .map(
              ([field, messages]) =>
                `${field}: ${(messages as string[]).join(", ")}`
            )
            .join(" | ");
        } else {
          error.value = "Registration failed. Please check your input.";
        }
      } else {
        error.value = "An unexpected error occurred during registration.";
      }
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function tryAutoLogin(router?: Router) {
    console.log("Auth Store: tryAutoLogin called.");
    if (!accessToken.value) {
      user.value = null;
      return;
    }
    if (user.value) {
      return;
    }
    isLoading.value = true;
    try {
      await axios.post("/token/verify/", { token: accessToken.value });
      await fetchUser(router);
    } catch (verificationError: any) {
      if (
        axios.isAxiosError(verificationError) &&
        verificationError.response?.data?.code === "token_not_valid"
      ) {
        const refreshed = await refreshTokenAction(router);
        if (!refreshed) {
          // logout() is called within refreshTokenAction if it fails hard
        }
      } else {
        await logout(router);
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function refreshTokenAction(router?: Router): Promise<boolean> {
    const currentRefreshToken = refreshToken.value;
    if (!currentRefreshToken) {
      await logout(router);
      return false;
    }
    try {
      const response = await axios.post("/token/refresh/", {
        refresh: currentRefreshToken,
      });
      const newAccess = response.data.access;
      const newRefresh = response.data.refresh;

      localStorage.setItem("accessToken", newAccess);
      accessToken.value = newAccess;
      if (newRefresh) {
        localStorage.setItem("refreshToken", newRefresh);
        refreshToken.value = newRefresh;
      }
      await fetchUser(router);
      return true;
    } catch (err) {
      await logout(router);
      return false;
    }
  }

  function clearError() {
    error.value = null;
  }

  return {
    accessToken,
    refreshToken,
    user,
    isLoggedIn,
    authUser,
    authLoading,
    authError,
    hasArtistProfile,
    artistProfileId,
    isStaff, // expose isStaff
    login,
    logout,
    fetchUser,
    register,
    tryAutoLogin,
    refreshTokenAction,
    clearError,
  };
});
