/**
 * BioID API client — Axios instance with auth interceptors,
 * retry logic, and typed response helpers.
 */
import axios, { AxiosError, type AxiosRequestConfig } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// ── Main API instance ────────────────────────────────────────────────────────
export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── Auth interceptor — attach JWT on every request ───────────────────────────
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("bioid_access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — handle 401 token refresh ─────────────────────────
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as AxiosRequestConfig & { _retry?: boolean };
    
    // Do not intercept 401s on auth routes (login/refresh) to avoid infinite loops
    if (original?.url?.includes('/auth/login') || original?.url?.includes('/auth/refresh')) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refresh = localStorage.getItem("bioid_refresh_token");
        if (refresh) {
          // FastAPI expects refresh_token_str as a query parameter
          const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh?refresh_token_str=${refresh}`);
          localStorage.setItem("bioid_access_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("bioid_refresh_token", data.refresh_token);
          }
          api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
          if (original.headers) {
            original.headers.Authorization = `Bearer ${data.access_token}`;
          }
          return api(original);
        }
      } catch {
        localStorage.removeItem("bioid_access_token");
        localStorage.removeItem("bioid_refresh_token");
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Typed API service ─────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/api/v1/auth/login", new URLSearchParams({
      username: email, password, grant_type: "password",
    }), { headers: { "Content-Type": "application/x-www-form-urlencoded" } }),

  register: (data: { name: string; email: string; password: string }) =>
    api.post("/api/v1/auth/register", data),

  /** Exchange a Firebase ID token for a NeoFace JWT pair. */
  googleSignIn: (idToken: string) =>
    api.post("/api/v1/auth/google", { id_token: idToken }),

  me: () => api.get("/api/v1/auth/me"),

  logout: () => api.post("/api/v1/auth/logout"),
};

export const enrollmentApi = {
  enroll: (formData: FormData) =>
    api.post("/api/v1/enrollment", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  validateFrame: (formData: FormData) =>
    api.post("/api/v1/enrollment/validate-frame", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  getStatus: (userId: string) => api.get(`/api/v1/enrollment/${userId}`),
  deleteEnrollment: (userId: string) => api.delete(`/api/v1/enrollment/${userId}`),
};

export const verificationApi = {
  verify: (formData: FormData, threshold?: number) =>
    api.post(`/api/v1/verify${threshold ? `?threshold=${threshold}` : ""}`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
};

export const dashboardApi = {
  getUsers: () => api.get("/api/v1/dashboard/users"),
  getVerifications: () => api.get("/api/v1/dashboard/verifications"),
  getSuccessRate: () => api.get("/api/v1/dashboard/success-rate"),
  getLogs: (page = 1, pageSize = 50) =>
    api.get(`/api/v1/dashboard/logs?page=${page}&page_size=${pageSize}`),
  getAnalytics: (days = 7) => api.get(`/api/v1/dashboard/analytics?days=${days}`),
  getHealth: () => api.get("/api/v1/dashboard/health"),
  getPaymentsOverview: () => api.get("/api/v1/dashboard/payments/overview"),
  getPaymentsDaily: (days = 14) => api.get(`/api/v1/dashboard/payments/daily?days=${days}`),
  getPaymentsRecent: (limit = 10) => api.get(`/api/v1/dashboard/payments/recent?limit=${limit}`)
};

export const usersApi = {
  list: (page = 1, pageSize = 20) =>
    api.get(`/api/v1/users?page=${page}&page_size=${pageSize}`),
  get: (userId: string) => api.get(`/api/v1/users/${userId}`),
  update: (userId: string, data: Record<string, unknown>) =>
    api.patch(`/api/v1/users/${userId}`, data),
  deactivate: (userId: string) => api.delete(`/api/v1/users/${userId}`),
};

export const paymentsApi = {
  authorize: (formData: FormData) => 
    api.post("/api/v1/payments/authorize", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  getHistory: (page = 1, pageSize = 20) => api.get(`/api/v1/payments/history?page=${page}&page_size=${pageSize}`),
  getAllAdmin: (page = 1, pageSize = 50) => api.get(`/api/v1/payments/admin/all?page=${page}&page_size=${pageSize}`)
};

export const merchantsApi = {
  list: () => api.get("/api/v1/merchants/"),
  create: (data: any) => api.post("/api/v1/merchants/", data),
  get: (id: string) => api.get(`/api/v1/merchants/${id}`),
  /** Admin: mark merchant as KYB-verified */
  verify: (id: string) => api.patch(`/api/v1/merchants/${id}/verify`),
  deactivate: (id: string) => api.delete(`/api/v1/merchants/${id}`),
};

export const bankAccountsApi = {
  list: () => api.get("/api/v1/bank_accounts/"),
  link: (data: any) => api.post("/api/v1/bank_accounts/link", data),
  /** Sets a linked account as the default for payment settlement */
  setDefault: (id: string) => api.patch(`/api/v1/bank_accounts/${id}/default`),
  unlink: (id: string) => api.delete(`/api/v1/bank_accounts/${id}`),
};

export const biometricsApi = {
  enrollIris: (formData: FormData) => api.post("/api/v1/biometrics/enroll/iris", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  enrollFingerprint: (formData: FormData) => api.post("/api/v1/biometrics/enroll/fingerprint", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  verifyMulti: (formData: FormData) => api.post("/api/v1/biometrics/verify", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  getStatus: () => api.get("/api/v1/biometrics/status"),
  /** Self-service: delete all enrolled face embeddings so user can re-enroll */
  deleteFace: () => api.delete("/api/v1/biometrics/face"),
  /** Self-service: delete all enrolled iris data */
  deleteIris: () => api.delete("/api/v1/biometrics/iris"),
  /** Self-service: delete all enrolled fingerprint templates */
  deleteFingerprint: () => api.delete("/api/v1/biometrics/fingerprint"),
};


// ── Trust Engine APIs ──────────────────────────────────────────────────────

export const livenessApi = {
  /** Passive liveness — MiniFASNetV1+V2 anti-spoof check */
  check: (formData: FormData) =>
    api.post("/api/v1/liveness/check", formData, { headers: { "Content-Type": "multipart/form-data" } }),

  /** Generate a randomized active liveness challenge */
  generateChallenge: (sessionId?: string, lastChallengeType?: string) => {
    const fd = new FormData();
    if (sessionId) fd.append("session_id", sessionId);
    if (lastChallengeType) fd.append("last_challenge_type", lastChallengeType);
    return api.post("/api/v1/liveness/challenge", fd, { headers: { "Content-Type": "multipart/form-data" } });
  },

  /** Verify a challenge frame */
  verifyChallenge: (formData: FormData) =>
    api.post("/api/v1/liveness/verify", formData, { headers: { "Content-Type": "multipart/form-data" } }),
};

export const emotionApi = {
  /** Analyze facial emotion from image */
  analyze: (formData: FormData) =>
    api.post("/api/v1/emotion/analyze", formData, { headers: { "Content-Type": "multipart/form-data" } }),
};

export const headPoseApi = {
  /** Estimate pitch, roll, yaw from face image */
  estimate: (formData: FormData) =>
    api.post("/api/v1/headpose", formData, { headers: { "Content-Type": "multipart/form-data" } }),
};

export const deepfakeApi = {
  /** Detect AI-generated / deepfake faces */
  check: (formData: FormData) =>
    api.post("/api/v1/deepfake/check", formData, { headers: { "Content-Type": "multipart/form-data" } }),
};

export const deviceTrustApi = {
  /** Assess device integrity from client-collected signals */
  assess: (signals: Record<string, unknown>) =>
    api.post("/api/v1/device/assess", signals),
};

export const behavioralApi = {
  /** Submit a batch of behavioral events (mouse/keyboard/touch) */
  submitEvents: (events: Array<{ event_type: string; metrics: Record<string, unknown> }>, sessionId?: string) =>
    api.post("/api/v1/behavior/events", { events, session_id: sessionId }),

  /** Real-time behavioral score without persisting */
  score: (events: Array<{ event_type: string; metrics: Record<string, unknown> }>, sessionId?: string) =>
    api.post("/api/v1/behavior/score", { events, session_id: sessionId }),

  /** Get current user's behavioral profile */
  getProfile: () => api.get("/api/v1/behavior/profile"),
};

export const riskApi = {
  /** Compute NeoFace Trust Score from component signals */
  computeScore: (input: {
    face_score?: number;
    liveness_score?: number;
    deepfake_score?: number;
    behavior_score?: number;
    device_trust_score?: number;
    location_trust?: number;
    fingerprint_trust?: number;
    session_id?: string;
    transaction_id?: string;
    transaction_amount?: number;
  }) => api.post("/api/v1/risk/score", input),

  /** Get risk score history for current user */
  getHistory: (page = 1, pageSize = 20) =>
    api.get(`/api/v1/risk/history?page=${page}&page_size=${pageSize}`),
};

export const webrtcApi = {
  /** Establish WebRTC connection by sending SDP offer */
  offer: (offer: { sdp: string; type: string }) =>
    api.post("/api/v1/webrtc/offer", offer),
};

export const continuousAuthApi = {
  /** Start a continuous auth session after login */
  startSession: (checkInterval = 30, deviceId?: string) => {
    const fd = new FormData();
    fd.append("check_interval", String(checkInterval));
    if (deviceId) fd.append("device_id", deviceId);
    return api.post("/api/v1/continuous-auth/session/start", fd, { headers: { "Content-Type": "multipart/form-data" } });
  },

  /** Submit a periodic check frame */
  check: (formData: FormData) =>
    api.post("/api/v1/continuous-auth/session/check", formData, { headers: { "Content-Type": "multipart/form-data" } }),

  /** End the session */
  endSession: (sessionToken: string, reason = "user_logout") => {
    const fd = new FormData();
    fd.append("session_token", sessionToken);
    fd.append("reason", reason);
    return api.post("/api/v1/continuous-auth/session/end", fd, { headers: { "Content-Type": "multipart/form-data" } });
  },

  /** Get session status */
  getStatus: (sessionToken: string) =>
    api.get(`/api/v1/continuous-auth/session/${sessionToken}`),
};

export const webAuthnApi = {
  /** Step 1: Get registration challenge from server */
  registerBegin: () => api.post("/api/v1/webauthn/register/begin"),

  /** Step 2: Submit attestation after navigator.credentials.create() */
  registerComplete: (body: {
    credential_id: string;
    raw_id: string;
    response: Record<string, string>;
    type: string;
    device_name: string;
    device_metadata?: Record<string, unknown>;
  }) => api.post("/api/v1/webauthn/register/complete", body),

  /** Step 1: Get authentication challenge */
  authBegin: () => api.post("/api/v1/webauthn/authenticate/begin"),

  /** Step 2: Submit assertion after navigator.credentials.get() */
  authComplete: (body: {
    credential_id: string;
    raw_id: string;
    response: Record<string, string>;
    type: string;
  }) => api.post("/api/v1/webauthn/authenticate/complete", body),

  /** List all enrolled devices */
  listDevices: () => api.get("/api/v1/webauthn/devices"),

  /** Rename a device */
  renameDevice: (credId: string, name: string) =>
    api.patch(`/api/v1/webauthn/devices/${credId}`, { device_name: name }),

  /** Revoke (delete) a device */
  revokeDevice: (credId: string) => api.delete(`/api/v1/webauthn/devices/${credId}`),

  /** Toggle fingerprint payment signing for a device */
  togglePayments: (credId: string, enabled: boolean) =>
    api.patch(`/api/v1/webauthn/devices/${credId}/payments`, { enabled }),

  /** Begin payment challenge (returns WebAuthn options + payment details) */
  paymentBegin: (body: { amount: number; currency: string; merchant_name: string; description?: string }) =>
    api.post("/api/v1/webauthn/payment/begin", body),

  /** Complete payment with signed assertion */
  paymentComplete: (body: {
    transaction_ref: string;
    credential_id: string;
    raw_id: string;
    response: Record<string, string>;
    type: string;
  }) => api.post("/api/v1/webauthn/payment/complete", body),
};

export const trustEngineApi = {
  /**
   * Match live camera frame against ONLY the logged-in user's enrolled face embeddings.
   * Returns face_match_score (0-100) for the Trust Score. Completely user-scoped.
   */
  verifyFace: (formData: FormData) =>
    api.post("/api/v1/trust-engine/verify-face", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),

  /**
   * Check whether the logged-in user has enrolled face data for the Trust Engine.
   * Used to show the enrollment gate if face is not yet registered.
   */
  getEnrollmentStatus: () =>
    api.get("/api/v1/trust-engine/enrollment-status"),
};
