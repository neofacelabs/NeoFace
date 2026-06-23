"use client";
/**
 * FirebaseAuthProvider
 * ---------------------
 * Runs once at the app root. Subscribes to Firebase's persistent auth state
 * and keeps the Zustand store in sync.
 *
 * Fix for the "login loop" bug:
 *   The original code read `isAuthenticated` from a stale closure in useEffect,
 *   meaning the value was always `false` on the first render. Every time
 *   onAuthStateChanged fired it would re-set tokens/user and trigger a
 *   re-render, causing the dashboard guard to briefly see isAuthenticated=false
 *   and redirect back to /login.
 *
 *   Solution: read live state via useAuthStore.getState() inside the callback
 *   so we always get the current value, not the captured closure value.
 */

import { useEffect } from "react";
import { subscribeToAuthState } from "@/lib/firebase-auth";
import { useAuthStore } from "@/store/auth";
import type { User } from "@/types";
import type { User as FirebaseUser } from "firebase/auth";

function buildUserFromFirebase(fbUser: FirebaseUser): User {
  return {
    id: fbUser.uid,
    name: fbUser.displayName ?? fbUser.email?.split("@")[0] ?? "User",
    email: fbUser.email ?? "",
    role: "user",
    is_active: true,
    is_enrolled: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

export function FirebaseAuthProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  useEffect(() => {
    const unsubscribe = subscribeToAuthState((fbUser) => {
      // Always read fresh state via getState() — never rely on a closure value
      // which would be stale and always appear as `false` on first mount.
      const { isAuthenticated, setFirebaseUser, setUser, setTokens } =
        useAuthStore.getState();

      if (fbUser) {
        // Sync the Firebase user reference regardless
        setFirebaseUser(fbUser);

        // Only set user/tokens if there's no existing backend session.
        // This prevents overwriting a real backend JWT with a Firebase pseudo-token.
        if (!isAuthenticated) {
          const neoUser = buildUserFromFirebase(fbUser);
          setUser(neoUser);
          // Use Firebase UID as a pseudo-token so auth guards pass
          setTokens(
            `firebase-${fbUser.uid}`,
            `firebase-refresh-${fbUser.uid}`
          );
        }
      } else {
        // Firebase signed out — clear the firebase user reference.
        // Do NOT log out a backend-only session (they signed in via email/pw).
        setFirebaseUser(null);
      }
    });

    return () => unsubscribe();
    // Empty deps: subscribe exactly once for the lifetime of the app.
    // All state reads happen via getState() inside the callback.
  }, []);

  return <>{children}</>;
}
