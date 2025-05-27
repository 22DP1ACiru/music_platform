import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import type { Router } from "vue-router";
import { usePlayerStore } from "./player";

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
  const isLoading = ref(false); // Renamed to avoid conflict with local component isLoading vars
  const error = ref<string | null>(null); // Renamed

  const playerStore = usePlayerStore();

  const isLoggedIn = computed(() => !!accessToken.value && !!user.value); // User must also be loaded
  const authUser = computed(() => user.value);
  const authLoading = computed(() => isLoading.value); // Expose isLoading as authLoading
  const authError = computed(() => error.value); // Expose error as authError

  const hasArtistProfile = computed(
    () => !!user.value?.profile?.artist_profile_data
  );
  const artistProfileId = computed(
    () => user.value?.profile?.artist_profile_data?.id || null
  );

  async function fetchUser(router?: Router) {
    if (!accessToken.value) {
      user.value = null;
      return; // No token, no user to fetch
    }
    // Do not set isLoading.value = true here if tryAutoLogin already does it.
    // Let the calling function (tryAutoLogin) manage the overall loading state.
    // error.value = null; // Clear previous errors for this specific action

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
        // If profile fetch fails (e.g. 404 if no profile exists yet), user base data might still be valid.
        // Only logout if it's an auth error (401)
        if (
          axios.isAxiosError(profileError) &&
          profileError.response?.status === 401
        ) {
          console.warn(
            "Auth Store: Profile fetch failed with 401. Logging out."
          );
          await logout(router);
          return; // Exit early as logout will clear user state
        }
        // Otherwise, profileData remains null, which is acceptable for users without profiles.
      }
      user.value = {
        ...userResponse.data,
        profile: profileData,
      };
      console.log("Auth Store: Fetched user and profile data:", user.value);
    } catch (err: any) {
      console.error("Auth Store: Failed to fetch user base data:", err);
      // error.value = "Could not fetch user details."; // Set specific error for this action
      // If fetching base user data fails with 401, it means token is bad.
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        console.warn(
          "Auth Store: Access token invalid/expired during fetchUser base. Logging out."
        );
        await logout(router); // This will set user.value to null
      } else {
        // For other errors, we might not want to clear the user if they were already partially loaded.
        // Or, clear them if fetchUser is critical for app state.
        // For now, let logout handle full clearing.
        user.value = null; // Clear user if any part of the fetch fails fundamentally.
      }
    }
    // isLoading is managed by the caller (tryAutoLogin)
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
        // Fetch user immediately after successful token acquisition
        await fetchUser(router);
        if (user.value && router) {
          const redirectPath =
            (router.currentRoute.value.query.redirect as string) || "/";
          router.push(redirectPath);
        } else if (!user.value) {
          // This case means tokens were received but user fetch failed
          error.value = "Login succeeded but failed to fetch user details.";
          // Keep tokens, user might retry or app might work partially
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
      throw err; // Re-throw for the component to catch if needed
    } finally {
      isLoading.value = false;
    }
  }

  async function logout(router?: Router) {
    // Clear local storage and reactive refs
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    accessToken.value = null;
    refreshToken.value = null;
    user.value = null;
    isLoading.value = false; // Ensure loading is false on logout
    error.value = null; // Clear any auth errors

    playerStore.resetPlayerState(); // Reset player state on logout

    try {
      const { useCartStore } = await import("./cart"); // Dynamic import
      const cartStore = useCartStore();
      cartStore.cart = null; // Reset cart state
    } catch (e) {
      console.error(
        "AuthStore: Error accessing/resetting cartStore during logout:",
        e
      );
    }

    console.log("Auth Store: Logged Out.");
    if (router) {
      try {
        // Only redirect if currently on a page that requires auth
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
      throw err; // Re-throw for component
    } finally {
      isLoading.value = false;
    }
  }

  async function tryAutoLogin(router?: Router) {
    console.log("Auth Store: tryAutoLogin called.");
    if (!accessToken.value) {
      console.log("Auth Store: No access token found for auto-login.");
      user.value = null; // Ensure user is null if no token
      return; // No token, can't auto-login
    }

    if (user.value) {
      console.log(
        "Auth Store: User data already loaded, skipping auto-login logic."
      );
      return; // User already loaded, no need to re-verify/fetch unless forced
    }

    isLoading.value = true; // Set loading state for the auto-login process
    // error.value = null; // Clear previous general auth errors

    try {
      console.log("Auth Store: Verifying existing token...");
      await axios.post("/token/verify/", { token: accessToken.value });
      console.log(
        "Auth Store: Token verified successfully. Fetching user data..."
      );
      await fetchUser(router); // Fetch user data since token is valid
    } catch (verificationError: any) {
      console.warn(
        "Auth Store: Token verification failed or token expired.",
        verificationError
      );
      if (
        axios.isAxiosError(verificationError) &&
        verificationError.response?.data?.code === "token_not_valid"
      ) {
        console.log(
          "Auth Store: Attempting token refresh due to invalid access token."
        );
        const refreshed = await refreshTokenAction(router); // Attempt to refresh
        if (!refreshed) {
          console.warn(
            "Auth Store: Token refresh also failed during auto-login. User remains logged out."
          );
          // logout() is called within refreshTokenAction if it fails hard
        } else {
          console.log(
            "Auth Store: Token refreshed successfully during auto-login. User data should be fetched (done by refreshTokenAction)."
          );
        }
      } else {
        // Other verification error, potentially network. Treat as logout.
        console.error(
          "Auth Store: Unknown error during token verification, logging out.",
          verificationError
        );
        await logout(router);
      }
    } finally {
      isLoading.value = false; // End loading state for auto-login process
    }
  }

  async function refreshTokenAction(router?: Router): Promise<boolean> {
    const currentRefreshToken = refreshToken.value;
    if (!currentRefreshToken) {
      console.error("Auth Store: No refresh token to attempt refresh.");
      await logout(router);
      return false;
    }
    // isLoading.value = true; // Manage loading state if this action is called independently
    try {
      console.log("Auth Store: Attempting token refresh...");
      const response = await axios.post("/token/refresh/", {
        refresh: currentRefreshToken,
      });
      const newAccess = response.data.access;
      const newRefresh = response.data.refresh; // Backend might send new refresh token

      localStorage.setItem("accessToken", newAccess);
      accessToken.value = newAccess;
      if (newRefresh) {
        localStorage.setItem("refreshToken", newRefresh);
        refreshToken.value = newRefresh;
      } else {
        // If backend doesn't rotate refresh tokens, it might not send one back.
        // This is fine, the old one is still valid until its own expiry.
      }
      console.log(
        "Auth Store: Token refresh successful. Fetching user data..."
      );
      await fetchUser(router); // Fetch user data with new access token
      return true;
    } catch (err) {
      console.error("Auth Store: Token refresh failed critically:", err);
      await logout(router); // Logout if refresh fails
      return false;
    } finally {
      // isLoading.value = false;
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
    authLoading, // Use the computed property
    authError, // Use the computed property
    hasArtistProfile,
    artistProfileId,
    login,
    logout,
    fetchUser, // Expose if needed directly, though tryAutoLogin and login handle it.
    register,
    tryAutoLogin,
    refreshTokenAction, // Expose if needed by interceptor or other parts
    clearError,
  };
});
