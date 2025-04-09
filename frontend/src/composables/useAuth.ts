import { ref, computed } from "vue";

// Reactive refs to hold token state
// Initialize from localStorage if tokens exist
const accessToken = ref<string | null>(localStorage.getItem("accessToken"));
const refreshToken = ref<string | null>(localStorage.getItem("refreshToken"));

// Computed property to easily check login status
const isLoggedIn = computed(() => !!accessToken.value);

// Function to handle login (stores tokens, updates refs)
const login = (access: string, refresh: string) => {
  localStorage.setItem("accessToken", access);
  localStorage.setItem("refreshToken", refresh);
  accessToken.value = access;
  refreshToken.value = refresh;
  console.log("Auth state updated: Logged In");
};

// Function to handle logout (clears tokens, updates refs)
const logout = () => {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  accessToken.value = null;
  refreshToken.value = null;
  console.log("Auth state updated: Logged Out");
  // Optionally redirect to home or login page
  // router.push({ name: 'home' }); // Need to import router if redirecting here
};

// Function to get the current access token (needed for API calls)
const getAccessToken = () => {
  return accessToken.value;
};

// Export the reactive state and functions
export function useAuth() {
  return {
    isLoggedIn,
    login,
    logout,
    getAccessToken, // Expose function to get token
    // refreshToken can also be exposed if needed for refresh logic
  };
}
