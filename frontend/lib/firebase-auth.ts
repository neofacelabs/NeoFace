import {
  signInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged,
  type User as FirebaseUser,
} from "firebase/auth";
import { auth, googleProvider } from "./firebase";

/**
 * Open the Google sign-in popup.
 * Returns the Firebase User on success, throws on failure/cancel.
 */
export async function signInWithGoogle(): Promise<FirebaseUser> {
  const result = await signInWithPopup(auth, googleProvider);
  return result.user;
}

/**
 * Sign the current user out of Firebase.
 * Does NOT touch the Zustand store — call store.logout() separately.
 */
export async function firebaseLogout(): Promise<void> {
  await firebaseSignOut(auth);
}

/**
 * Subscribe to Firebase auth state changes.
 * Returns an unsubscribe function.
 */
export function subscribeToAuthState(
  callback: (user: FirebaseUser | null) => void
): () => void {
  return onAuthStateChanged(auth, callback);
}

export { auth };
