// ── Auth ─────────────────────────────────────────────────────────────────────
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  phone?: string;
  role: "user" | "admin";
  is_active: boolean;
  is_enrolled: boolean;
  created_at: string;
  updated_at: string;
}

// ── Enrollment ───────────────────────────────────────────────────────────────
export interface FaceQualityResult {
  image_index: number;
  passed: boolean;
  width: number;
  height: number;
  blur_score: number;
  face_detected: boolean;
  face_count: number;
  quality_score: number;
  rejection_reason?: string;
}

export interface EnrollmentResponse {
  user_id: string;
  status: string;
  message: string;
  confidence: number;
  images_processed: number;
  quality_results: FaceQualityResult[];
  enrolled_at: string;
}

export interface EnrollmentStatus {
  user_id: string;
  is_enrolled: boolean;
  enrollment_count: number;
  last_enrolled_at?: string;
}

// ── Verification ─────────────────────────────────────────────────────────────
export interface LivenessResult {
  is_live: boolean;
  score: number;
  blink_detected: boolean;
  head_turn_detected: boolean;
  smile_detected: boolean;
  checks_passed: number;
  checks_total: number;
  anti_spoof_score: number;
  method: string;
}

export interface VerificationResponse {
  authenticated: boolean;
  user_id?: string;
  user_name?: string;
  confidence_score: number;
  liveness_score: number;
  liveness_detail: LivenessResult;
  threshold_used: number;
  failure_reason?: string;
  verified_at: string;
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export interface UserStats {
  total_users: number;
  enrolled_users: number;
  active_users: number;
  enrollment_rate: number;
  as_of: string;
}

export interface VerificationStats {
  total_verifications: number;
  successful_verifications: number;
  failed_verifications: number;
  success_rate: number;
  as_of: string;
}

export interface AuthLogEntry {
  id: string;
  user_id?: string;
  confidence_score?: number;
  liveness_score?: number;
  authentication_result: boolean;
  failure_reason?: string;
  ip_address?: string;
  timestamp: string;
}

export interface AuthLogList {
  total: number;
  page: number;
  page_size: number;
  logs: AuthLogEntry[];
}

export interface DailyStatPoint {
  date: string;
  total: number;
  successful: number;
}

export interface AnalyticsData {
  period_days: number;
  daily_stats: DailyStatPoint[];
  as_of: string;
}

// ── Store ─────────────────────────────────────────────────────────────────────
export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export interface EnrollmentState {
  step: number;
  capturedImages: string[];
  isProcessing: boolean;
  result?: EnrollmentResponse;
  error?: string;
  setStep: (step: number) => void;
  addImage: (dataUrl: string) => void;
  resetImages: () => void;
  setProcessing: (v: boolean) => void;
  setResult: (r: EnrollmentResponse) => void;
  setError: (e: string) => void;
  reset: () => void;
}

export interface VerificationState {
  isVerifying: boolean;
  result?: VerificationResponse;
  error?: string;
  setVerifying: (v: boolean) => void;
  setResult: (r: VerificationResponse) => void;
  setError: (e: string) => void;
  reset: () => void;
}

// ── Payments & Merchants ──────────────────────────────────────────────────────
export interface Merchant {
  id: string;
  name: string;
  business_type: string;
  is_verified: boolean;
  sandbox_mode: boolean;
  created_at: string;
}

export interface BankAccount {
  id: string;
  bank_name: string;
  last_four: string;
  account_type: string;
  is_default: boolean;
  is_verified: boolean;
}

export interface BiometricBreakdown {
  modality: "face" | "iris" | "fingerprint";
  matched: boolean;
  confidence_score: number;
}

export interface Transaction {
  id: string;
  amount: number;
  currency: string;
  status: "pending" | "completed" | "failed" | "refunded";
  merchant_id?: string;
  bank_account_id?: string;
  authentication_result: boolean;
  failure_reason?: string;
  fusion_score?: number;
  created_at: string;
  biometric_details?: BiometricBreakdown[];
}

export interface PaymentOverview {
  total_transactions: number;
  authorized_transactions: number;
  failed_transactions: number;
  total_volume_usd: number;
  authorization_rate: number;
  modality_breakdown: Record<string, number>;
  as_of: string;
}

export interface PaymentDailyStats {
  date: string;
  total_count: number;
  successful_count: number;
  volume: number;
}

// ── Trust Engine — Passive Liveness ──────────────────────────────────────────
export interface PassiveLivenessResult {
  liveness_score: number;          // 0.0–1.0
  is_live: boolean;
  confidence: number;              // 0–100
  attack_type: string;             // none | photo | screen | replay | mask | virtual_camera
  method: string;
  inference_ms: number;
  model_available: boolean;
  v1_score?: number;
  v2_score?: number;
}

// ── Trust Engine — Active Liveness Challenge ──────────────────────────────────
export interface ActiveChallengeResponse {
  challenge_id: string;
  challenge_type: string;
  steps: string[];
  descriptions: string[];
  difficulty: string;
  nonce: string;
  expires_in_seconds: number;
}

export interface ChallengeVerifyResponse {
  challenge_completed: boolean;
  challenge_type: string;
  steps_completed: string[];
  steps_pending: string[];
  confidence: number;
  inference_ms: number;
  failure_reason?: string;
}

// ── Trust Engine — Emotion ────────────────────────────────────────────────────
export interface EmotionResult {
  emotion: string;                 // happy | neutral | surprise | angry | sad | fear | disgust
  confidence: number;              // 0–100
  all_scores: Record<string, number>;
  method: string;
  inference_ms: number;
  model_available: boolean;
}

// ── Trust Engine — Head Pose ──────────────────────────────────────────────────
export interface HeadPoseResult {
  pitch: number;
  yaw: number;
  roll: number;
  is_frontal: boolean;
  is_extreme: boolean;
  method: string;
  inference_ms: number;
}

// ── Trust Engine — Deepfake Detection ────────────────────────────────────────
export interface DeepfakeResult {
  deepfake_probability: number;    // 0.0–1.0
  is_deepfake: boolean;
  attack_category: string;         // face_swap | gan_face | synthetic_avatar | deepfake_video | none
  method: string;
  confidence: number;
  inference_ms: number;
  model_available: boolean;
  efficientnet_score?: number;
  xceptionnet_score?: number;
}

// ── Trust Engine — Device Trust ───────────────────────────────────────────────
export interface DeviceTrustResult {
  device_trust: number;            // 0–100
  platform: string;
  rooted: boolean;
  jailbroken: boolean;
  emulator: boolean;
  usb_debugging: boolean;
  virtual_camera: boolean;
  headless_browser: boolean;
  automation_detected: boolean;
  risk_flags: string[];
}

// ── Trust Engine — Behavioral Biometrics ─────────────────────────────────────
export interface BehaviorScoreResult {
  behavior_score: number;          // 0–100
  is_anomalous: boolean;
  anomaly_score: number;
  method: string;
  component_scores: Record<string, number>;
  risk_flags: string[];
}

export interface BehaviorProfileResult {
  user_id: string;
  total_events: number;
  is_baseline_established: boolean;
  avg_mouse_speed?: number;
  avg_typing_speed_wpm?: number;
  avg_swipe_velocity?: number;
  profile_version: number;
  updated_at?: string;
}

// ── Trust Engine — Risk Score ─────────────────────────────────────────────────
export interface RiskScoreResult {
  final_trust_score: number;       // 0–100
  decision: "approve" | "step_up" | "reject";
  component_scores: {
    face_score?: number;
    liveness_score?: number;
    deepfake_score?: number;
    behavior_score?: number;
    device_trust_score?: number;
    location_trust?: number;
    fingerprint_trust?: number;
  };
  weights_used: Record<string, number>;
  contributing_factors: number;
  hard_blocked: boolean;
  hard_block_reason?: string;
  risk_flags: string[];
  explanation: string;
  score_id?: string;
}

// ── Trust Engine — Continuous Auth ───────────────────────────────────────────
export interface ContinuousSession {
  session_token: string;
  status: "active" | "suspended" | "terminated" | "reauth_required";
  current_trust_score: number;
  check_interval_seconds: number;
  started_at: string;
  last_verified_at?: string;
  reauth_count: number;
}

export interface ContinuousCheckResult {
  session_token: string;
  action: "continue" | "reauth_required" | "suspend" | "terminate";
  trust_score: number;
  check_score: number;
  status: string;
  evaluated_at: string;
  next_check_in_seconds: number;
}

// ── Trust Engine — Full Scan (composite result) ───────────────────────────────
export interface TrustEngineScanResult {
  passive_liveness?: PassiveLivenessResult;
  emotion?: EmotionResult;
  head_pose?: HeadPoseResult;
  deepfake?: DeepfakeResult;
  risk?: RiskScoreResult;
  scan_duration_ms: number;
  timestamp: string;
}
