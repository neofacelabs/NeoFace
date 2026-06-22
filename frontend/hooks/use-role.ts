/**
 * useRole — Shared hook for Role-Based Access Control across the dashboard.
 *
 * Reads the authenticated user's role from the Zustand auth store and
 * exposes convenient boolean helpers so components don't need to do
 * raw string comparisons everywhere.
 *
 * Usage:
 *   const { isAdmin, isUser, role } = useRole();
 */

"use client";
import { useAuthStore } from "@/store/auth";

export type UserRole = "admin" | "user";

export function useRole() {
  const user = useAuthStore((s) => s.user);
  const role = (user?.role ?? "user") as UserRole;

  return {
    role,
    isAdmin: role === "admin",
    isUser:  role === "user",
    /** True if user object is fully loaded (not just authenticated). */
    isLoaded: user !== null,
  };
}
