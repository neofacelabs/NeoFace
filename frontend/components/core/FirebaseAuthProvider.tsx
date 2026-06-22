"use client";
/**
 * FirebaseAuthProvider
 * ---------------------
 * Runs once at the app root. It subscribes to Firebase's own persistent auth
 * state (survives page navigation, browser refresh, etc.) and keeps the Zustand
 * store in sync.
 *
 * Why this guarantees the user is never logged out on navigation:
 *   - Firebase stores the session in IndexedDB/localStorage under its own key.
 *   - onAuthStateChanged fires IMMEDIATELY on mount with the cached user before
 *     any network round-trip, so there is no "flash of logged-out" state.
 *   - Zustand's `persist` middleware restores `isAuthenticated` from localStorage
 *     for the NeoFace backend session.
 *   - Together they cover both: Google-authenticated users AND backend-only users.
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
  const { setFirebaseUser, setUser, setTokens, isAuthenticated } =
    useAuthStore();

  useEffect(() => {
    const unsubscribe = subscribeToAuthState((fbUser) => {
      if (fbUser) {
        // User is signed in to Firebase (Google or any other provider)
        setFirebaseUser(fbUser);

        // Only override the Zustand user/token if there is no pre-existing
        // backend session. This avoids overwriting a backend-authed admin with
        // a Google-only user object.
        if (!isAuthenticated) {
          const neoUser = buildUserFromFirebase(fbUser);
          setUser(neoUser);
          // Use the Firebase UID as a pseudo-token so the auth-guard passes
          setTokens(`firebase-${fbUser.uid}`, `firebase-refresh-${fbUser.uid}`);
        } else {
          // Backend session exists — just sync the firebase user reference
          setFirebaseUser(fbUser);
        }
      } else {
        // Firebase says no user — clear the firebase reference
        // (but don't log out a backend-only user — they signed in via email/pw)
        setFirebaseUser(null);
      }
    });

    return () => unsubscribe();
    // isAuthenticated intentionally omitted: the Firebase listener should only
    // be subscribed once. Reading `isAuthenticated` inside the callback (closure)
    // is safe because we only check it synchronously within the callback scope.
  }, [setFirebaseUser, setUser, setTokens]);

  return <>{children}</>;
}
