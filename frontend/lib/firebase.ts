import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getAnalytics, isSupported } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyC2NjpwDirHQIUW8PwuKu1kDss_GFecCWg",
  authDomain: "neoface-payments.firebaseapp.com",
  projectId: "neoface-payments",
  storageBucket: "neoface-payments.firebasestorage.app",
  messagingSenderId: "555226105345",
  appId: "1:555226105345:web:ae8911de1d75632b64a200",
  measurementId: "G-P3RN58JKTL",
};

// Prevent duplicate initialization in Next.js hot-reload
const app = getApps().length ? getApp() : initializeApp(firebaseConfig);

// Auth
export const auth = getAuth(app);

// Google provider — request email + profile by default
export const googleProvider = new GoogleAuthProvider();
googleProvider.addScope("email");
googleProvider.addScope("profile");
// Always show account chooser even if only one account is signed in
googleProvider.setCustomParameters({ prompt: "select_account" });

// Analytics (browser-only, ignored in SSR)
if (typeof window !== "undefined") {
  isSupported().then((yes) => {
    if (yes) getAnalytics(app);
  });
}

export default app;
