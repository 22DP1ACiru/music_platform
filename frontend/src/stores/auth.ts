import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import type { Router } from "vue-router";
import { usePlayerStore } from "./player"; // Import the player store

// --- Interfaces to match backend serializers ---
interface ArtistProfileForAuth {
  id: number;
  name: string;
}

interface UserProfileForAuth {
  id: number;
  bio: string | null;
  profile_picture: string | null;
  location: string | null;
  website_url: string | null;
  artist_profile_data: ArtistProfileForAuth | null;
}

interface User {
  id: number;
  username: string;
  email: string;
  profile: UserProfileForAuth | null;
}

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string | null>(localStorage.getItem("accessToken"));
  const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));
  const user = ref<User | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const playerStore = usePlayerStore(); // Initialize player store

  const isLoggedIn = computed(() => !!accessToken.value);
  const authUser = computed(() => user.value);
  const hasArtistProfile = computed(
    () => !!user.value?.profile?.artist_profile_data
  );
  const artistProfileId = computed(
    () => user.value?.profile?.artist_profile_data?.id || null
  );

  async function fetchUser(router?: Router) {
    if (!accessToken.value) {
      user.value = null;
      return;
    }
    isLoading.value = true;
    error.value = null;
    try {
      const userResponse = await axios.get<Omit<User, "profile">>("/users/me/");
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
          console.warn(
            "Auth Store: Profile fetch failed with 401. Logging out."
          );
          await logout(router);
        }
      }
      user.value = {
        ...userResponse.data,
        profile: profileData,
      };
      console.log("Auth Store: Fetched user and profile data:", user.value);
    } catch (err: any) {
      console.error("Auth Store: Failed to fetch user base data:", err);
      error.value = "Could not fetch user details.";
      user.value = null;
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        console.warn(
          "Auth Store: Access token invalid/expired during fetchUser base. Logging out."
        );
        await logout(router);
      }
    } finally {
      isLoading.value = false;
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
        console.log("Auth Store: Login successful, tokens stored.");
        await fetchUser(router);
        if (user.value && router) {
          const redirectPath =
            (router.currentRoute.value.query.redirect as string) || "/";
          router.push(redirectPath);
        } else if (!user.value) {
          error.value =
            "Login succeeded but failed to fetch user details fully.";
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

    playerStore.resetPlayerState(); // Reset player state on logout

    console.log("Auth Store: Logged Out, player state reset.");
    if (router) {
      try {
        if (
          router.currentRoute.value.name !== "login" &&
          router.currentRoute.value.meta.requiresAuth
        ) {
          await router.push({ name: "login" });
        } else if (
          router.currentRoute.value.name !== "home" &&
          !router.currentRoute.value.meta.requiresAuth
        ) {
          // No specific redirect needed if on a public page already
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
    if (accessToken.value) {
      isLoading.value = true;
      try {
        console.log("Auth Store: Verifying existing token...");
        await axios.post("/token/verify/", { token: accessToken.value });
        console.log("Auth Store: Token verified successfully.");
        await fetchUser(router);
        // Player state is loaded by playerStore itself
      } catch (verificationError) {
        console.warn(
          "Auth Store: Token verification failed or token expired.",
          verificationError
        );
        const refreshed = await refreshTokenAction(router);
        if (!refreshed) {
          console.warn(
            "Auth Store: Token refresh also failed during auto-login. User remains logged out."
          );
        } else {
          console.log(
            "Auth Store: Token refreshed successfully during auto-login. User data should be fetched."
          );
        }
      } finally {
        isLoading.value = false;
      }
    } else {
      console.log("Auth Store: No token found for auto-login.");
      user.value = null;
    }
  }

  async function refreshTokenAction(router?: Router) {
    const currentRefreshToken = refreshToken.value;
    if (!currentRefreshToken) {
      console.error("Auth Store: No refresh token to attempt refresh.");
      await logout(router);
      return false;
    }
    try {
      console.log("Auth Store: Attempting token refresh...");
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
      console.log("Auth Store: Token refresh successful.");
      await fetchUser(router);
      return true;
    } catch (err) {
      console.error("Auth Store: Token refresh failed:", err);
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
    authLoading: isLoading,
    authError: error,
    hasArtistProfile,
    artistProfileId,
    login,
    logout,
    fetchUser,
    register,
    tryAutoLogin,
    refreshTokenAction,
    clearError,
  };
});
