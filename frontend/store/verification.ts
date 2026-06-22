import { create } from "zustand";
import type { VerificationResponse, VerificationState } from "@/types";

export const useVerificationStore = create<VerificationState>()((set) => ({
  isVerifying: false,
  result: undefined,
  error: undefined,

  setVerifying: (v) => set({ isVerifying: v }),
  setResult: (r) => set({ result: r, error: undefined, isVerifying: false }),
  setError: (e) => set({ error: e, isVerifying: false }),
  reset: () => set({ isVerifying: false, result: undefined, error: undefined }),
}));
