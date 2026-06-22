import { create } from "zustand";
import type { EnrollmentResponse, EnrollmentState } from "@/types";

export const useEnrollmentStore = create<EnrollmentState>()((set) => ({
  step: 1,
  capturedImages: [],
  isProcessing: false,
  result: undefined,
  error: undefined,

  setStep: (step) => set({ step }),
  addImage: (dataUrl) =>
    set((s) => ({ capturedImages: [...s.capturedImages, dataUrl] })),
  resetImages: () => set({ capturedImages: [] }),
  setProcessing: (v) => set({ isProcessing: v }),
  setResult: (r) => set({ result: r, error: undefined }),
  setError: (e) => set({ error: e }),
  reset: () =>
    set({
      step: 1,
      capturedImages: [],
      isProcessing: false,
      result: undefined,
      error: undefined,
    }),
}));
