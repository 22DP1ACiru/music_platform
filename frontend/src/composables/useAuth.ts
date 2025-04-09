import { ref, computed } from "vue";
import axios from "axios";

interface User {
  id: number;
  username: string;
  email: string;
}

// Reactive refs to hold token state
// Initialize from localStorage if tokens exist
const accessToken = ref<string | null>(localStorage.getItem("accessToken"));
const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));
const user = ref<User | null>(null);
const authIsLoading = ref(false);
const authError = ref<string | null>(null);

// Computed property to easily check login status
const isLoggedIn = computed(() => !!accessToken.value);

// Function to fetch user data from the API
const fetchUser = async () => {
  if (!accessToken.value) {
    user.value = null; // Ensure user is null if no token
    return; // Don't fetch if no token
  }
  authIsLoading.value = true;
  authError.value = null;
  try {
    // Request interceptor will add the token header
    const response = await axios.get<User>("/users/me/"); // Use GET request
    user.value = response.data;
    console.log("Fetched user data:", user.value);
  } catch (error) {
    console.error("Failed to fetch user data:", error);
    authError.value = "Could not fetch user details.";
    // Potentially token is invalid/expired, might need logout or refresh here
    // For now, just clear user data
    user.value = null;
    // Consider calling logout() if fetch fails due to auth error (e.g., 401)
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      logout(); // Log out if token is invalid
    }
  } finally {
    authIsLoading.value = false;
  }
};

// Function to handle login (stores tokens, updates refs)
const login = async (access: string, refresh: string) => {
  localStorage.setItem("accessToken", access);
  localStorage.setItem("refreshToken", refresh);
  accessToken.value = access;
  refreshToken.value = refresh;
  console.log("Auth state updated: Logged In");
  // Fetch user details immediately after successful login
  await fetchUser();
};

// Function to handle logout (clears tokens, updates refs)
const logout = () => {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  accessToken.value = null;
  refreshToken.value = null;
  user.value = null; // Clear user data on logout
  console.log("Auth state updated: Logged Out");
};

// Function to get the current access token (needed for API calls)
const getAccessToken = () => {
  return accessToken.value;
};

// Export the reactive state and functions
export function useAuth() {
  return {
    isLoggedIn,
    user,
    authIsLoading,
    authError,
    login,
    logout,
    getAccessToken,
    fetchUser,
  };
}
