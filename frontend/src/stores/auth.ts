import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import type { Router } from "vue-router";

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
  const user = ref<User | null>(null); // User state will now include profile
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const isLoggedIn = computed(() => !!accessToken.value);
  const authUser = computed(() => user.value); // This will now have user.value.profile
  const hasArtistProfile = computed(
    () => !!user.value?.profile?.artist_profile_data
  );
  const artistProfileId = computed(
    () => user.value?.profile?.artist_profile_data?.id || null
  );

  async function fetchUser() {
    if (!accessToken.value) {
      user.value = null;
      return;
    }
    isLoading.value = true;
    error.value = null;
    try {
      // Fetch basic user data
      const userResponse = await axios.get<Omit<User, "profile">>("/users/me/"); // Omit profile as it's not in /users/me
      let profileData: UserProfileForAuth | null = null;

      // Fetch profile data
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
        // Decide if this is a critical failure. For now, user can exist without profile fully loaded.
        // If profile is essential for basic app operation post-login, handle appropriately.
      }

      user.value = {
        ...userResponse.data,
        profile: profileData, // Attach fetched profile data
      };

      console.log("Auth Store: Fetched user and profile data:", user.value);
    } catch (err: any) {
      console.error("Auth Store: Failed to fetch user base data:", err);
      error.value = "Could not fetch user details.";
      user.value = null;
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        console.warn(
          "Auth Store: Access token invalid/expired during fetchUser. Logging out."
        );
        await logout();
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
        await fetchUser(); // This will now also attempt to fetch profile
        if (user.value && router) {
          router.push({ name: "home" });
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
        error.value = err.response.data.detail || "Login failed.";
      } else {
        error.value = "An unexpected network error occurred during login.";
      }
      throw error;
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
    console.log("Auth Store: Logged Out");
    // Clear default headers for axios if you've set them globally
    // delete axios.defaults.headers.common["Authorization"];
    if (router) {
      try {
        // Check if already on a public page to avoid redundant navigation or errors
        if (router.currentRoute.value.meta.requiresAuth) {
          await router.push({ name: "login" });
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
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function tryAutoLogin() {
    console.log("Auth Store: Checking for existing token on load...");
    if (accessToken.value) {
      // Attempt to verify token with backend? (Optional, but good for robustness)
      // Example:
      // try {
      //   await axios.post('/token/verify/', { token: accessToken.value });
      //   console.log("Auth Store: Token verified.");
      //   await fetchUser(); // Fetch user if token is valid
      // } catch (verificationError) {
      //   console.warn("Auth Store: Token verification failed or token expired.", verificationError);
      //   await refreshTokenAction(); // Try to refresh if verification fails
      // }
      await fetchUser(); // Fetch user if token exists (includes profile fetch attempt)
    } else {
      console.log("Auth Store: No token found.");
    }
  }

  async function refreshTokenAction(router?: Router) {
    // Pass router to handle logout on failure
    const currentRefreshToken = refreshToken.value;
    if (!currentRefreshToken) {
      console.error("Auth Store: No refresh token to attempt refresh.");
      await logout(router);
      return false;
    }
    isLoading.value = true;
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
      console.log("Auth Store: Token refresh successful.");
      // If you set Authorization header on axios.defaults, update it here too
      // axios.defaults.headers.common["Authorization"] = `Bearer ${newAccess}`;

      // After successful refresh, re-fetch user data as roles/profile might have changed
      // or to ensure consistency if the old token caused partial data load.
      await fetchUser();

      return true;
    } catch (err) {
      console.error("Auth Store: Token refresh failed:", err);
      await logout(router);
      return false;
    } finally {
      isLoading.value = false;
    }
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
  };
});
