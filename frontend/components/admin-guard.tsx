/**
 * AdminGuard — Route protection component for admin-only pages.
 *
 * If the logged-in user is not an admin:
 *   1. Shows a brief "Access Denied" screen (so the redirect isn't jarring)
 *   2. Redirects to /dashboard after 1.5 seconds
 *
 * Usage (wrap the entire page content):
 *   export default function AdminPage() {
 *     return (
 *       <AdminGuard>
 *         <YourPageContent />
 *       </AdminGuard>
 *     );
 *   }
 */

"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ShieldOff, ArrowLeft } from "lucide-react";
import { useRole } from "@/hooks/use-role";
import { useAuthStore } from "@/store/auth";

interface AdminGuardProps {
  children: React.ReactNode;
}

export function AdminGuard({ children }: AdminGuardProps) {
  const { isAdmin, isLoaded } = useRole();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);

  // Wait for Zustand persist to rehydrate before checking auth
  useEffect(() => {
    if ((useAuthStore as any).persist?.hasHydrated()) {
      setHydrated(true);
    } else {
      const unsub = (useAuthStore as any).persist?.onFinishHydration(() => {
        setHydrated(true);
      });
      return () => unsub?.();
    }
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) {
      router.replace("/login");
      return;
    }
    if (isLoaded && !isAdmin) {
      const timer = setTimeout(() => router.replace("/dashboard"), 1800);
      return () => clearTimeout(timer);
    }
  }, [hydrated, isAdmin, isLoaded, isAuthenticated, router]);

  // Still hydrating or loading user from store — show nothing to avoid flash
  if (!hydrated || !isLoaded || !isAuthenticated) return null;

  // Non-admin: show access denied screen
  if (!isAdmin) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center justify-center min-h-[70vh] text-center gap-6"
      >
        <motion.div
          animate={{ scale: [1, 1.06, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          className="w-24 h-24 rounded-full flex items-center justify-center"
          style={{
            background: "rgba(248,113,113,0.1)",
            border: "2px solid rgba(248,113,113,0.3)",
            boxShadow: "0 0 40px rgba(248,113,113,0.1)",
          }}
        >
          <ShieldOff size={38} style={{ color: "#f87171" }} />
        </motion.div>

        <div className="space-y-2">
          <h2 className="text-2xl font-bold text-white">Access Restricted</h2>
          <p className="text-[14px] text-[rgba(255,255,255,0.4)] max-w-sm">
            This page requires <strong className="text-[rgba(248,113,113,0.8)]">Admin</strong> privileges.
            You&apos;ll be redirected to your dashboard shortly.
          </p>
        </div>

        {/* Countdown bar */}
        <div className="w-48 h-1 rounded-full bg-[rgba(255,255,255,0.06)] overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: "#f87171" }}
            initial={{ width: "100%" }}
            animate={{ width: "0%" }}
            transition={{ duration: 1.8, ease: "linear" }}
          />
        </div>

        <button
          onClick={() => router.replace("/dashboard")}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-[12px] font-medium transition-all"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.1)",
            color: "rgba(255,255,255,0.4)",
          }}
        >
          <ArrowLeft size={12} />
          Go to Dashboard
        </button>
      </motion.div>
    );
  }

  return <>{children}</>;
}
