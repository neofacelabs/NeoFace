import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthState, User } from "@/types";
import type { User as FirebaseUser } from "firebase/auth";

// Extend AuthState with Firebase-specific fields
interface ExtendedAuthState extends AuthState {
  firebaseUser: FirebaseUser | null;
  setFirebaseUser: (fbUser: FirebaseUser | null) => void;
}

export const useAuthStore = create<ExtendedAuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      firebaseUser: null,

      setUser: (user: User | null) =>
        set({ user, isAuthenticated: !!user }),

      setFirebaseUser: (fbUser: FirebaseUser | null) =>
        set({ firebaseUser: fbUser }),

      setTokens: (access: string, refresh: string) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("bioid_access_token", access);
          localStorage.setItem("bioid_refresh_token", refresh);
        }
        set({ accessToken: access, isAuthenticated: true });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("bioid_access_token");
          localStorage.removeItem("bioid_refresh_token");
        }
        // Note: Firebase sign-out is handled separately via firebaseLogout()
        // in the component that calls logout, so Firebase state stays consistent.
        set({ user: null, accessToken: null, isAuthenticated: false, firebaseUser: null });
      },
    }),
    {
      name: "bioid-auth",
      // Don't persist firebaseUser — Firebase SDK restores it from its own
      // persistent session on every page load via onAuthStateChanged.
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
