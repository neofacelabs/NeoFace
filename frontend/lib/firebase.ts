import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getAnalytics, isSupported } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyBawjm-wP3rbxM4-XiBRAVU4evu9USQiDA",
  authDomain: "neoface-labs.firebaseapp.com",
  projectId: "neoface-labs",
  storageBucket: "neoface-labs.firebasestorage.app",
  messagingSenderId: "397627831854",
  appId: "1:397627831854:web:7aa9bb4b64bed9dd1611bf",
  measurementId: "G-362MZ4Y9T5",
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
