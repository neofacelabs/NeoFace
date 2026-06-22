"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck, ShieldAlert, ShieldOff, Eye, Activity,
  Brain, Cpu, Smartphone, AlertTriangle, UserCheck, UserX,
  Zap, RefreshCw, Camera, Info, ChevronDown, ChevronUp, Target,
  Loader2, ArrowRight, Lock,
} from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import {
  livenessApi, emotionApi, headPoseApi, deepfakeApi,
  deviceTrustApi, riskApi, trustEngineApi,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  PassiveLivenessResult, EmotionResult, HeadPoseResult,
  DeepfakeResult, RiskScoreResult,
} from "@/types";

// ── Types ───────────────────────────────────────────────────────────────────────
interface FaceMatchResult {
  face_enrolled: boolean;
  face_match: boolean;
  face_match_score: number;
  cosine_similarity?: number;
  embedding_count: number;
  message: string;
  inference_ms: number;
}

// ── Score ring ─────────────────────────────────────────────────────────────────
function ScoreRing({
  score, size = 72, color, label,
}: { score: number; size?: number; color: string; label: string }) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(100, Math.max(0, score));
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90" style={{ display: "block" }}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={7} />
          <motion.circle
            cx={size / 2} cy={size / 2} r={r} fill="none"
            stroke={color} strokeWidth={7} strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - (pct / 100) * circ }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-bold" style={{ color }}>{pct.toFixed(0)}</span>
        </div>
      </div>
      <span className="text-[10px] text-[rgba(255,255,255,0.35)] text-center leading-tight">{label}</span>
    </div>
  );
}

// ── Trust score badge ──────────────────────────────────────────────────────────
function TrustBadge({ score, decision }: { score: number; decision: string }) {
  const config = {
    approve:  { color: "#00E5A8", bg: "rgba(0,229,168,0.12)", border: "rgba(0,229,168,0.3)", icon: ShieldCheck, label: "APPROVED" },
    step_up:  { color: "#f59e0b", bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", icon: ShieldAlert, label: "STEP-UP" },
    reject:   { color: "#f87171", bg: "rgba(248,113,113,0.12)", border: "rgba(248,113,113,0.3)", icon: ShieldOff, label: "REJECTED" },
  }[decision] ?? { color: "#9ca3af", bg: "rgba(156,163,175,0.12)", border: "rgba(156,163,175,0.3)", icon: ShieldCheck, label: "PENDING" };

  const Icon = config.icon;
  return (
    <div className="flex flex-col items-center gap-2">
      <motion.div
        initial={{ scale: 0.7, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 14 }}
        className="w-20 h-20 rounded-full flex items-center justify-center relative"
        style={{ background: config.bg, border: `2px solid ${config.border}`, boxShadow: `0 0 30px ${config.color}25` }}
      >
        <Icon size={32} style={{ color: config.color }} />
        <motion.div
          animate={{ scale: [1, 1.5], opacity: [0.3, 0] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
          className="absolute inset-0 rounded-full"
          style={{ border: `2px solid ${config.color}` }}
        />
      </motion.div>
      <div className="text-center">
        <div className="text-3xl font-bold text-white">{score.toFixed(0)}</div>
        <div className="text-[10px] font-bold tracking-widest mt-0.5" style={{ color: config.color }}>{config.label}</div>
      </div>
    </div>
  );
}

// ── Module card ────────────────────────────────────────────────────────────────
function ModuleCard({
  title, icon: Icon, color, status, children, loading, collapsible = false,
}: {
  title: string; icon: any; color: string; status: "idle" | "pass" | "fail" | "loading";
  children: React.ReactNode; loading?: boolean; collapsible?: boolean;
}) {
  const [open, setOpen] = useState(true);
  const statusDot = {
    idle:    "bg-[rgba(255,255,255,0.15)]",
    loading: "bg-yellow-400 animate-pulse",
    pass:    "bg-[#00E5A8]",
    fail:    "bg-[#f87171]",
  }[status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl overflow-hidden"
      style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}
    >
      <button
        onClick={() => collapsible && setOpen(o => !o)}
        className={cn("w-full flex items-center gap-2.5 px-4 py-3", collapsible && "cursor-pointer")}
        style={{ borderBottom: open ? "1px solid rgba(255,255,255,0.06)" : "none" }}
      >
        <div className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
          style={{ background: `${color}15`, border: `1px solid ${color}25` }}>
          <Icon size={13} style={{ color }} />
        </div>
        <span className="text-[12.5px] font-semibold text-white flex-1 text-left">{title}</span>
        {loading && <Loader2 size={11} className="animate-spin text-[rgba(255,255,255,0.3)]" />}
        <span className={cn("w-2 h-2 rounded-full shrink-0", statusDot)}
          style={status === "pass" ? { boxShadow: "0 0 4px #00E5A8" } : status === "fail" ? { boxShadow: "0 0 4px #f87171" } : {}} />
        {collapsible && (
          open ? <ChevronUp size={12} className="text-[rgba(255,255,255,0.25)]" />
               : <ChevronDown size={12} className="text-[rgba(255,255,255,0.25)]" />
        )}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: "hidden" }}
          >
            <div className="px-4 py-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Key-value row ──────────────────────────────────────────────────────────────
function KVRow({ label, value, highlight }: { label: string; value: string | number | boolean; highlight?: string }) {
  const v = typeof value === "boolean" ? (value ? "Yes" : "No") : String(value);
  return (
    <div className="flex items-center justify-between text-[11.5px] py-1">
      <span className="text-[rgba(255,255,255,0.38)]">{label}</span>
      <span className="font-medium" style={{ color: highlight ?? "rgba(255,255,255,0.75)" }}>{v}</span>
    </div>
  );
}

// ── Emotion bar ────────────────────────────────────────────────────────────────
function EmotionBar({ emotion, score, active }: { emotion: string; score: number; active: boolean }) {
  const COLORS: Record<string, string> = {
    happy: "#00E5A8", neutral: "#9ca3af", surprise: "#f59e0b",
    angry: "#f87171", sad: "#818cf8", fear: "#f97316", disgust: "#a78bfa",
  };
  const color = COLORS[emotion] ?? "#9ca3af";
  return (
    <div className="flex items-center gap-2 text-[10.5px]">
      <span className="w-14 text-right text-[rgba(255,255,255,0.4)] capitalize">{emotion}</span>
      <div className="flex-1 h-1.5 rounded-full bg-[rgba(255,255,255,0.05)]">
        <motion.div
          className="h-full rounded-full"
          style={{ background: active ? color : "rgba(255,255,255,0.12)" }}
          initial={{ width: 0 }}
          animate={{ width: `${score}%` }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      <span className="w-8 font-semibold" style={{ color: active ? color : "rgba(255,255,255,0.3)" }}>
        {score.toFixed(0)}%
      </span>
    </div>
  );
}

// ── Enrollment Gate ─────────────────────────────────────────────────────────────
function EnrollmentGate({ onNavigate }: { onNavigate: () => void }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col items-center justify-center min-h-[60vh] text-center gap-8 px-4"
    >
      {/* Icon */}
      <div className="relative">
        <motion.div
          animate={{ scale: [1, 1.08, 1] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          className="w-28 h-28 rounded-full flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(0,194,255,0.15))",
            border: "2px solid rgba(99,102,241,0.4)",
            boxShadow: "0 0 60px rgba(99,102,241,0.15)",
          }}
        >
          <Lock size={44} style={{ color: "#818cf8" }} />
        </motion.div>
        {/* Orbiting dot */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0"
          style={{ transformOrigin: "center" }}
        >
          <div
            className="absolute w-3 h-3 rounded-full"
            style={{
              background: "#00E5A8",
              top: "4px",
              left: "50%",
              transform: "translateX(-50%)",
              boxShadow: "0 0 8px #00E5A8",
            }}
          />
        </motion.div>
      </div>

      {/* Text */}
      <div className="space-y-3 max-w-md">
        <h2 className="text-2xl font-bold text-white">Face Enrollment Required</h2>
        <p className="text-[14px] text-[rgba(255,255,255,0.45)] leading-relaxed">
          The NeoFace Trust Engine verifies <strong className="text-white">your identity</strong> by matching your live face against your enrolled biometric data.
        </p>
        <p className="text-[13px] text-[rgba(255,255,255,0.3)] leading-relaxed">
          Your biometric data is encrypted, stored privately, and <strong className="text-[rgba(255,255,255,0.5)]">only visible to you</strong>. No other user can access your scans or trust scores.
        </p>
      </div>

      {/* Steps */}
      <div className="grid grid-cols-3 gap-4 max-w-lg w-full">
        {[
          { step: "1", icon: Camera, label: "Enroll Face", desc: "Capture 5 angles", color: "#818cf8" },
          { step: "2", icon: ShieldCheck, label: "Store Securely", desc: "Encrypted in DB", color: "#00E5A8" },
          { step: "3", icon: Zap, label: "Run Scans", desc: "Your data only", color: "#f59e0b" },
        ].map(({ step, icon: Icon, label, desc, color }) => (
          <div key={step} className="flex flex-col items-center gap-2 p-4 rounded-2xl"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
              <Icon size={16} style={{ color }} />
            </div>
            <div className="text-[11px] font-semibold text-white">{label}</div>
            <div className="text-[10px] text-[rgba(255,255,255,0.3)]">{desc}</div>
          </div>
        ))}
      </div>

      {/* CTA */}
      <motion.button
        onClick={onNavigate}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.97 }}
        className="flex items-center gap-3 px-8 py-4 rounded-2xl text-[14px] font-bold transition-all"
        style={{
          background: "linear-gradient(135deg, rgba(99,102,241,0.35), rgba(0,194,255,0.25))",
          border: "1px solid rgba(99,102,241,0.5)",
          color: "white",
          boxShadow: "0 0 30px rgba(99,102,241,0.2)",
        }}
      >
        <Camera size={18} />
        Go to Identity & Enroll Face
        <ArrowRight size={16} />
      </motion.button>

      <p className="text-[11px] text-[rgba(255,255,255,0.2)]">
        After enrolling, return here to run your personalized Trust Engine scan
      </p>
    </motion.div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function TrustEnginePage() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string>();

  // ── Enrollment gate state ─────────────────────────────────────────────────
  const [enrollmentChecked, setEnrollmentChecked] = useState(false);
  const [faceEnrolled, setFaceEnrolled] = useState(false);
  const [enrolledEmbeddingCount, setEnrolledEmbeddingCount] = useState(0);

  const [scanning, setScanning] = useState(false);
  const [liveScanEnabled, setLiveScanEnabled] = useState(true);
  const [silentScanning, setSilentScanning] = useState(false);
  const [passiveLiveness, setPassiveLiveness] = useState<PassiveLivenessResult | null>(null);
  const [emotion, setEmotion] = useState<EmotionResult | null>(null);
  const [headPose, setHeadPose] = useState<HeadPoseResult | null>(null);
  const [deepfake, setDeepfake] = useState<DeepfakeResult | null>(null);
  const [faceMatch, setFaceMatch] = useState<FaceMatchResult | null>(null);
  const [riskScore, setRiskScore] = useState<RiskScoreResult | null>(null);
  const [scanMs, setScanMs] = useState<number>(0);
  const [moduleStatus, setModuleStatus] = useState<Record<string, "idle" | "pass" | "fail" | "loading">>({
    faceMatch: "idle", liveness: "idle", emotion: "idle", headpose: "idle", deepfake: "idle", risk: "idle",
  });

  const isScanningRef = useRef(false);
  const liveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // ── Check enrollment status on mount ──────────────────────────────────────
  useEffect(() => {
    const checkEnrollment = async () => {
      try {
        const { data } = await trustEngineApi.getEnrollmentStatus();
        setFaceEnrolled(data.face_enrolled);
        setEnrolledEmbeddingCount(data.face_embedding_count ?? 0);
      } catch (err) {
        console.warn("Enrollment check failed:", err);
        setFaceEnrolled(false);
      } finally {
        setEnrollmentChecked(true);
      }
    };
    checkEnrollment();
  }, []);

  // ── Camera ────────────────────────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    setCameraError(undefined);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play();
          setCameraReady(true);
        };
      }
    } catch {
      setCameraError("Camera access required for Trust Engine scanning.");
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    setCameraReady(false);
  }, []);

  // Only start camera if user is enrolled
  useEffect(() => {
    if (enrollmentChecked && faceEnrolled) {
      startCamera();
      return stopCamera;
    }
  }, [enrollmentChecked, faceEnrolled, startCamera, stopCamera]);

  // ── Capture frame ─────────────────────────────────────────────────────────
  const captureFrame = useCallback((): Promise<Blob | null> => {
    return new Promise(resolve => {
      if (!videoRef.current || !canvasRef.current) return resolve(null);
      const v = videoRef.current, c = canvasRef.current;

      // Validate the video is actually playing and has a frame
      if (v.readyState < 2 || v.videoWidth === 0 || v.videoHeight === 0) {
        return resolve(null);
      }

      // Ensure minimum 640×480 so InsightFace can detect faces reliably.
      // Webcams sometimes stream at 320×240 which is too small for the model.
      const MIN_WIDTH = 640;
      const scale = v.videoWidth < MIN_WIDTH ? MIN_WIDTH / v.videoWidth : 1;
      c.width  = Math.round(v.videoWidth  * scale);
      c.height = Math.round(v.videoHeight * scale);

      const ctx = c.getContext("2d");
      if (!ctx) return resolve(null);
      ctx.drawImage(v, 0, 0, c.width, c.height);

      // 0.95 quality = better face detail for ArcFace embedding extraction
      c.toBlob(blob => resolve(blob), "image/jpeg", 0.95);
    });
  }, []);

  // Helper: build a FormData with the captured blob for multipart upload
  // NOTE: Blob is a static byte buffer and can be reused across multiple FormData instances.
  const makeFormData = (blob: Blob, fieldName = "image") => {
    const f = new FormData();
    f.append(fieldName, blob, "frame.jpg");
    return f;
  };

  // ── Silent Scan (live polling) ─────────────────────────────────────────────
  const runScanSilent = async () => {
    if (!cameraReady) return;
    setSilentScanning(true);

    const t0 = performance.now();
    const blob = await captureFrame();
    if (!blob) { setSilentScanning(false); return; }

    // Run all modules in parallel including per-user face match
    const [livRes, emoRes, hpRes, dfRes, fmRes] = await Promise.allSettled([
      livenessApi.check(makeFormData(blob)),
      emotionApi.analyze(makeFormData(blob)),
      headPoseApi.estimate(makeFormData(blob)),
      deepfakeApi.check(makeFormData(blob)),
      trustEngineApi.verifyFace(makeFormData(blob)),
    ]);

    // Face match (user-specific)
    if (fmRes.status === "fulfilled") {
      const d = fmRes.value.data as FaceMatchResult;
      setFaceMatch(d);
      setModuleStatus(s => ({ ...s, faceMatch: d.face_match ? "pass" : "fail" }));
    } else {
      setModuleStatus(s => ({ ...s, faceMatch: "fail" }));
    }

    if (livRes.status === "fulfilled") {
      const d = livRes.value.data as PassiveLivenessResult;
      setPassiveLiveness(d);
      setModuleStatus(s => ({ ...s, liveness: d.is_live ? "pass" : "fail" }));
    } else {
      setModuleStatus(s => ({ ...s, liveness: "fail" }));
    }

    if (emoRes.status === "fulfilled") {
      const d = emoRes.value.data as EmotionResult;
      setEmotion(d);
      setModuleStatus(s => ({ ...s, emotion: "pass" }));
    } else {
      setModuleStatus(s => ({ ...s, emotion: "fail" }));
    }

    if (hpRes.status === "fulfilled") {
      const d = hpRes.value.data as HeadPoseResult;
      setHeadPose(d);
      setModuleStatus(s => ({ ...s, headpose: d.is_frontal ? "pass" : "fail" }));
    } else {
      setModuleStatus(s => ({ ...s, headpose: "fail" }));
    }

    if (dfRes.status === "fulfilled") {
      const d = dfRes.value.data as DeepfakeResult;
      setDeepfake(d);
      setModuleStatus(s => ({ ...s, deepfake: d.is_deepfake ? "fail" : "pass" }));
    } else {
      setModuleStatus(s => ({ ...s, deepfake: "fail" }));
    }

    // Build risk score using all signals including actual per-user face match
    try {
      const livData = livRes.status === "fulfilled" ? livRes.value.data : null;
      const dfData  = dfRes.status  === "fulfilled" ? dfRes.value.data  : null;
      const hpData  = hpRes.status  === "fulfilled" ? hpRes.value.data  : null;
      const fmData  = fmRes.status  === "fulfilled" ? fmRes.value.data  : null;

      const behaviorScore = hpData
        ? (hpData.is_frontal ? 88 : hpData.is_extreme ? 40 : 72)
        : 80;
      const deviceScore = deviceTrust ? deviceTrust.device_trust : 85;

      const { data: riskData } = await riskApi.computeScore({
        // Real face match score from this user's enrolled embeddings
        face_score:         fmData?.face_match_score ?? (livData?.is_live ? 65 : 30),
        liveness_score:     livData ? livData.confidence : undefined,
        deepfake_score:     dfData  ? (1 - dfData.deepfake_probability) * 100 : undefined,
        behavior_score:     behaviorScore,
        device_trust_score: deviceScore,
        location_trust:     88,
      });
      setRiskScore(riskData as RiskScoreResult);
      setModuleStatus(s => ({ ...s, risk: riskData.decision === "reject" ? "fail" : "pass" }));
    } catch {
      setModuleStatus(s => ({ ...s, risk: "fail" }));
    }

    setScanMs(Math.round(performance.now() - t0));
    setSilentScanning(false);
  };

  // ── Full scan ─────────────────────────────────────────────────────────────
  const runFullScan = async () => {
    if (!cameraReady || isScanningRef.current) return;
    isScanningRef.current = true;
    setScanning(true);
    setPassiveLiveness(null); setEmotion(null); setHeadPose(null);
    setDeepfake(null); setFaceMatch(null); setRiskScore(null);
    setModuleStatus({ faceMatch: "loading", liveness: "loading", emotion: "loading", headpose: "loading", deepfake: "loading", risk: "loading" });

    const t0 = performance.now();
    const blob = await captureFrame();
    if (!blob) { setScanning(false); isScanningRef.current = false; return; }

    const [livRes, emoRes, hpRes, dfRes, fmRes] = await Promise.allSettled([
      livenessApi.check(makeFormData(blob)),
      emotionApi.analyze(makeFormData(blob)),
      headPoseApi.estimate(makeFormData(blob)),
      deepfakeApi.check(makeFormData(blob)),
      trustEngineApi.verifyFace(makeFormData(blob)),
    ]);

    // Face match
    if (fmRes.status === "fulfilled") {
      const d = fmRes.value.data as FaceMatchResult;
      setFaceMatch(d);
      setModuleStatus(s => ({ ...s, faceMatch: d.face_match ? "pass" : "fail" }));
      if (!d.face_match) {
        toast.warning("Face not matched — position your face clearly in the oval");
      }
    } else {
      setModuleStatus(s => ({ ...s, faceMatch: "fail" }));
    }

    if (livRes.status === "fulfilled") {
      const d = livRes.value.data as PassiveLivenessResult;
      setPassiveLiveness(d);
      setModuleStatus(s => ({ ...s, liveness: d.is_live ? "pass" : "fail" }));
    } else {
      setModuleStatus(s => ({ ...s, liveness: "fail" }));
      toast.error("Liveness check failed");
    }

    if (emoRes.status === "fulfilled") {
      const d = emoRes.value.data as EmotionResult;
      setEmotion(d);
      setModuleStatus(s => ({ ...s, emotion: "pass" }));
    } else {
      setModuleStatus(s => ({ ...s, emotion: "fail" }));
    }

    if (hpRes.status === "fulfilled") {
      const d = hpRes.value.data as HeadPoseResult;
      setHeadPose(d);
      setModuleStatus(s => ({ ...s, headpose: d.is_frontal ? "pass" : "fail" }));
    } else {
      setModuleStatus(s => ({ ...s, headpose: "fail" }));
    }

    if (dfRes.status === "fulfilled") {
      const d = dfRes.value.data as DeepfakeResult;
      setDeepfake(d);
      setModuleStatus(s => ({ ...s, deepfake: d.is_deepfake ? "fail" : "pass" }));
    } else {
      setModuleStatus(s => ({ ...s, deepfake: "fail" }));
    }

    // Build risk score
    try {
      const livData = livRes.status === "fulfilled" ? livRes.value.data : null;
      const dfData  = dfRes.status  === "fulfilled" ? dfRes.value.data  : null;
      const hpData  = hpRes.status  === "fulfilled" ? hpRes.value.data  : null;
      const fmData  = fmRes.status  === "fulfilled" ? fmRes.value.data  : null;

      const behaviorScore = hpData
        ? (hpData.is_frontal ? 88 : hpData.is_extreme ? 40 : 72)
        : 80;
      const deviceScore = deviceTrust ? deviceTrust.device_trust : 85;

      const { data: riskData } = await riskApi.computeScore({
        face_score:         fmData?.face_match_score ?? (livData?.is_live ? 65 : 30),
        liveness_score:     livData ? livData.confidence : undefined,
        deepfake_score:     dfData  ? (1 - dfData.deepfake_probability) * 100 : undefined,
        behavior_score:     behaviorScore,
        device_trust_score: deviceScore,
        location_trust:     88,
      });
      setRiskScore(riskData as RiskScoreResult);
      setModuleStatus(s => ({ ...s, risk: riskData.decision === "reject" ? "fail" : "pass" }));
    } catch {
      setModuleStatus(s => ({ ...s, risk: "fail" }));
    }

    setScanMs(Math.round(performance.now() - t0));
    setScanning(false);
    isScanningRef.current = false;
  };

  // ── Live polling ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (cameraReady && liveScanEnabled && faceEnrolled) {
      const runPoll = async () => {
        if (isScanningRef.current) return;
        isScanningRef.current = true;
        try {
          await runScanSilent();
        } catch (err) {
          console.error("Live scan error:", err);
        } finally {
          isScanningRef.current = false;
        }
      };

      runPoll();
      liveTimerRef.current = setInterval(runPoll, 1500);
    } else {
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
    }

    return () => {
      if (liveTimerRef.current) {
        clearInterval(liveTimerRef.current);
        liveTimerRef.current = null;
      }
    };
  }, [cameraReady, liveScanEnabled, faceEnrolled]);

  // ── Device trust ──────────────────────────────────────────────────────────
  const [deviceTrust, setDeviceTrust] = useState<{ device_trust: number; risk_flags: string[]; virtual_camera: boolean; automation_detected: boolean } | null>(null);

  const assessDevice = useCallback(async () => {
    try {
      const cameras = await navigator.mediaDevices.enumerateDevices()
        .then(devs => devs.filter(d => d.kind === "videoinput").map(d => ({ label: d.label, deviceId: d.deviceId })));

      const signals = {
        platform: "web",
        device_id: `web-${navigator.userAgent.slice(0, 20)}`,
        navigator_webdriver: !!(navigator as any).webdriver,
        camera_ids: cameras,
        webgl_renderer: (() => {
          try {
            const c = document.createElement("canvas");
            const gl = c.getContext("webgl") as WebGLRenderingContext | null;
            if (!gl) return "";
            const ext = gl.getExtension("WEBGL_debug_renderer_info");
            return ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "";
          } catch { return ""; }
        })(),
      };

      const { data } = await deviceTrustApi.assess(signals);
      setDeviceTrust(data);
    } catch (err) {
      console.warn("Device assessment failed:", err);
    }
  }, []);

  useEffect(() => { assessDevice(); }, [assessDevice]);

  // ── Loading state ─────────────────────────────────────────────────────────
  if (!enrollmentChecked) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-4">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          >
            <Loader2 size={32} style={{ color: "#818cf8" }} />
          </motion.div>
          <p className="text-[13px] text-[rgba(255,255,255,0.3)]">Checking your biometric enrollment…</p>
        </div>
      </div>
    );
  }

  // ── Enrollment gate ───────────────────────────────────────────────────────
  if (!faceEnrolled) {
    return <EnrollmentGate onNavigate={() => router.push("/dashboard/identity")} />;
  }

  // ── Main scanner UI ───────────────────────────────────────────────────────
  const hasResults = passiveLiveness || emotion || headPose || deepfake || riskScore || faceMatch;

  return (
    <div className="space-y-6">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
          </div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">NeoFace Trust Engine</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
            Real-time biometric scan — matched against <strong className="text-[rgba(255,255,255,0.5)]">your enrolled identity only</strong>
          </p>
        </div>
        {hasResults && (
          <button onClick={runFullScan} disabled={scanning || !cameraReady}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-[12px] font-medium transition-all"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}>
            <RefreshCw size={12} className={scanning ? "animate-spin" : ""} />
            Rescan
          </button>
        )}
      </div>

      <div className="grid xl:grid-cols-[1fr,380px] gap-5">
        {/* ── LEFT — Camera + Scan ─────────────────────────────────────── */}
        <div className="space-y-4">
          {/* Camera card */}
          <div className="rounded-2xl overflow-hidden relative"
            style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="relative aspect-[4/3] bg-black">
              {cameraError ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6">
                  <Camera size={32} style={{ color: "rgba(255,255,255,0.15)" }} />
                  <p className="text-sm text-[rgba(255,255,255,0.3)] text-center">{cameraError}</p>
                  <button onClick={startCamera} className="px-4 py-2 rounded-xl text-sm font-medium"
                    style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8" }}>
                    Enable Camera
                  </button>
                </div>
              ) : (
                <>
                  <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />

                  {/* Face oval guide — large */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="relative" style={{ width: 340, height: 420 }}>
                      <motion.div
                        animate={{
                          borderColor: faceMatch?.face_match
                            ? ["rgba(0,229,168,0.9)", "rgba(0,229,168,0.5)", "rgba(0,229,168,0.9)"]
                            : (scanning || silentScanning)
                              ? ["rgba(99,102,241,0.8)", "rgba(0,229,168,0.8)", "rgba(99,102,241,0.8)"]
                              : "rgba(99,102,241,0.4)"
                        }}
                        transition={{ duration: 1.2, repeat: (scanning || silentScanning || !!faceMatch) ? Infinity : 0 }}
                        className="absolute inset-0 rounded-full border-2"
                      />
                      {/* Corners */}
                      {["top-0 left-0 border-t-2 border-l-2", "top-0 right-0 border-t-2 border-r-2",
                        "bottom-0 left-0 border-b-2 border-l-2", "bottom-0 right-0 border-b-2 border-r-2"].map((cls, i) => (
                        <motion.div key={i}
                          className={`absolute w-7 h-7 ${cls}`}
                          style={{ borderColor: faceMatch?.face_match ? "#00E5A8" : "#818cf8" }}
                          animate={{ opacity: (scanning || silentScanning) ? [1, 0.2, 1] : 1 }}
                          transition={{ duration: 0.7, repeat: (scanning || silentScanning) ? Infinity : 0, delay: i * 0.1 }}
                        />
                      ))}
                      {(scanning || silentScanning) && (
                        <div className="absolute inset-x-0 h-0.5"
                          style={{ background: "linear-gradient(90deg, transparent, #818cf8, transparent)", animation: "scanDown 2s linear infinite", top: 0 }} />
                      )}
                      {/* Face match result overlay */}
                      {faceMatch && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="absolute -bottom-10 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold"
                          style={{
                            background: faceMatch.face_match ? "rgba(0,229,168,0.15)" : "rgba(248,113,113,0.15)",
                            border: `1px solid ${faceMatch.face_match ? "rgba(0,229,168,0.4)" : "rgba(248,113,113,0.4)"}`,
                            color: faceMatch.face_match ? "#00E5A8" : "#f87171",
                          }}
                        >
                          {faceMatch.face_match
                            ? <><UserCheck size={12} /> Identity Verified — {faceMatch.face_match_score.toFixed(0)}% match</>
                            : <><UserX size={12} /> {faceMatch.face_match_score > 0 ? `Low match (${faceMatch.face_match_score.toFixed(0)}%)` : "Position your face"}</>
                          }
                        </motion.div>
                      )}
                    </div>
                  </div>

                  {/* Module overlay badges during scan */}
                  {scanning && (
                    <div className="absolute top-3 left-3 flex flex-col gap-1.5">
                      {[
                        { label: "Face Match", color: "#00E5A8" },
                        { label: "Passive Liveness", color: "#00C2FF" },
                        { label: "Deepfake", color: "#f87171" },
                        { label: "Emotion", color: "#f59e0b" },
                        { label: "Head Pose", color: "#818cf8" },
                      ].map(({ label, color }, i) => (
                        <motion.div key={label}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.1 }}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium"
                          style={{ background: "rgba(0,0,0,0.7)", border: `1px solid ${color}30`, color }}>
                          <Loader2 size={9} className="animate-spin" />
                          {label}
                        </motion.div>
                      ))}
                    </div>
                  )}

                  {/* Status badge */}
                  <div className="absolute top-3 right-3">
                    {cameraReady ? (
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px]"
                        style={{
                          background: "rgba(0,0,0,0.7)",
                          color: liveScanEnabled ? "#00E5A8" : "rgba(255,255,255,0.4)",
                          border: `1px solid ${liveScanEnabled ? "rgba(0,229,168,0.3)" : "rgba(255,255,255,0.15)"}`
                        }}>
                        <span className={cn("w-1.5 h-1.5 rounded-full", liveScanEnabled ? "bg-[#00E5A8] animate-pulse" : "bg-gray-500")} />
                        {liveScanEnabled ? "LIVE SCANNING" : "PAUSED"}
                      </div>
                    ) : null}
                  </div>

                  {scanMs > 0 && !scanning && (
                    <div className="absolute bottom-3 right-3 px-2.5 py-1 rounded-full text-[9.5px] font-medium"
                       style={{ background: "rgba(0,0,0,0.7)", color: "rgba(255,255,255,0.4)" }}>
                      Scan: {scanMs}ms
                    </div>
                  )}
                </>
              )}
              <canvas ref={canvasRef} className="hidden" />
            </div>

            {/* Scan button */}
            <div className="p-4">
              <motion.button
                onClick={() => setLiveScanEnabled(prev => !prev)}
                disabled={!cameraReady}
                whileTap={{ scale: 0.97 }}
                className="w-full py-3.5 rounded-xl text-[13.5px] font-bold flex items-center justify-center gap-2.5 transition-all"
                style={{
                  background: liveScanEnabled ? "rgba(0,229,168,0.1)" : "linear-gradient(135deg, rgba(99,102,241,0.25), rgba(0,194,255,0.2))",
                  border: `1px solid ${liveScanEnabled ? "rgba(0,229,168,0.4)" : "rgba(99,102,241,0.4)"}`,
                  color: liveScanEnabled ? "#00E5A8" : "white",
                  cursor: !cameraReady ? "not-allowed" : "pointer",
                  boxShadow: !liveScanEnabled && cameraReady ? "0 0 20px rgba(99,102,241,0.15)" : "none",
                }}
              >
                {liveScanEnabled ? (
                  <><span className="w-2 h-2 rounded-full bg-[#00E5A8] animate-ping mr-1" /> Live Scanning Active (Pause)</>
                ) : (
                  <><Target size={16} /> Resume Live Scanning</>
                )}
              </motion.button>
              <p className="text-center text-[10.5px] text-[rgba(255,255,255,0.2)] mt-2">
                {liveScanEnabled ? "Verifying against your enrolled face · all modules live" : "Click to resume real-time biometric scanning"}
              </p>
            </div>
          </div>

          {/* Module results grid */}
          <div className="grid sm:grid-cols-2 gap-3">
            {/* Face Match — Per-user */}
            <ModuleCard title="Face Identity Match" icon={UserCheck} color="#00E5A8"
              status={moduleStatus.faceMatch} loading={scanning} collapsible>
              {faceMatch ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <ScoreRing score={faceMatch.face_match_score} size={60}
                      color={faceMatch.face_match ? "#00E5A8" : "#f87171"} label="Match" />
                    <div className="space-y-1.5 flex-1">
                      <KVRow label="Matched?" value={faceMatch.face_match ? "✓ YES" : "✗ NO"}
                        highlight={faceMatch.face_match ? "#00E5A8" : "#f87171"} />
                      <KVRow label="Match Score" value={`${faceMatch.face_match_score.toFixed(1)}%`}
                        highlight={faceMatch.face_match_score >= 80 ? "#00E5A8" : faceMatch.face_match_score >= 65 ? "#f59e0b" : "#f87171"} />
                      {faceMatch.cosine_similarity != null && (
                        <KVRow label="Cosine Sim" value={faceMatch.cosine_similarity.toFixed(3)} />
                      )}
                      <KVRow label="Enrolled Faces" value={faceMatch.embedding_count} />
                      <KVRow label="Inference" value={`${faceMatch.inference_ms.toFixed(0)}ms`} />
                    </div>
                  </div>
                  <div className="mt-2 p-2 rounded-lg text-[10px]"
                    style={{
                      background: faceMatch.face_match ? "rgba(0,229,168,0.05)" : "rgba(248,113,113,0.05)",
                      border: `1px solid ${faceMatch.face_match ? "rgba(0,229,168,0.15)" : "rgba(248,113,113,0.15)"}`,
                      color: "rgba(255,255,255,0.4)"
                    }}>
                    {faceMatch.message}
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] py-2">
                  {scanning ? "Matching face against your enrolled embeddings…" : "Run a scan to verify your identity"}
                </p>
              )}
            </ModuleCard>

            {/* Passive Liveness */}
            <ModuleCard title="Passive Liveness" icon={Eye} color="#00C2FF"
              status={moduleStatus.liveness} loading={scanning} collapsible>
              {passiveLiveness ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <ScoreRing score={passiveLiveness.confidence} size={60} color={passiveLiveness.is_live ? "#00E5A8" : "#f87171"} label="Liveness" />
                    <div className="space-y-1.5 flex-1">
                      <KVRow label="Decision" value={passiveLiveness.is_live ? "LIVE" : "SPOOF"}
                        highlight={passiveLiveness.is_live ? "#00E5A8" : "#f87171"} />
                      <KVRow label="Attack Type" value={passiveLiveness.attack_type === "none" ? "None detected" : passiveLiveness.attack_type}
                        highlight={passiveLiveness.attack_type !== "none" ? "#f87171" : "#00E5A8"} />
                      <KVRow label="Method" value={passiveLiveness.method} />
                      <KVRow label="Inference" value={`${passiveLiveness.inference_ms.toFixed(0)}ms`} />
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] py-2">
                  {scanning ? "Analyzing frame with MiniFASNet ensemble…" : "Run a scan to see passive liveness results"}
                </p>
              )}
            </ModuleCard>

            {/* Emotion */}
            <ModuleCard title="Emotion Analysis" icon={Activity} color="#f59e0b"
              status={moduleStatus.emotion} loading={scanning} collapsible>
              {emotion ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="text-base font-bold text-white capitalize">{emotion.emotion}</span>
                      <span className="text-[rgba(255,255,255,0.3)] text-[11px] ml-2">{emotion.confidence.toFixed(0)}% confidence</span>
                    </div>
                    <span className="text-[10px] text-[rgba(255,255,255,0.2)]">{emotion.method}</span>
                  </div>
                  <div className="space-y-1">
                    {Object.entries(emotion.all_scores)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 5)
                      .map(([em, score]) => (
                        <EmotionBar key={em} emotion={em} score={score} active={em === emotion.emotion} />
                      ))}
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] py-2">
                  {scanning ? "Running MobileNetV3 emotion classifier…" : "Run a scan to analyze facial emotions"}
                </p>
              )}
            </ModuleCard>

            {/* Deepfake Detection */}
            <ModuleCard title="Deepfake Detection" icon={Brain} color="#f87171"
              status={moduleStatus.deepfake} loading={scanning} collapsible>
              {deepfake ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <ScoreRing
                      score={(1 - deepfake.deepfake_probability) * 100}
                      size={60}
                      color={deepfake.is_deepfake ? "#f87171" : "#00E5A8"}
                      label="Authenticity"
                    />
                    <div className="space-y-1.5 flex-1">
                      <KVRow label="Deepfake?" value={deepfake.is_deepfake ? "DETECTED" : "Clean"}
                        highlight={deepfake.is_deepfake ? "#f87171" : "#00E5A8"} />
                      <KVRow label="Probability" value={`${(deepfake.deepfake_probability * 100).toFixed(1)}%`}
                        highlight={deepfake.deepfake_probability > 0.5 ? "#f87171" : "#00E5A8"} />
                      <KVRow label="Category" value={deepfake.attack_category === "none" ? "—" : deepfake.attack_category}
                        highlight={deepfake.attack_category !== "none" ? "#f87171" : undefined} />
                      <KVRow label="Model" value={deepfake.method} />
                    </div>
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] py-2">
                  {scanning ? "Running EfficientNet-B4 + XceptionNet ensemble…" : "Run a scan to detect deepfakes"}
                </p>
              )}
            </ModuleCard>

            {/* Head Pose */}
            <ModuleCard title="Head Pose (3D)" icon={Cpu} color="#818cf8"
              status={moduleStatus.headpose} loading={scanning} collapsible>
              {headPose ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    {[
                      { label: "Pitch", value: headPose.pitch, color: "#00C2FF", desc: "up/down" },
                      { label: "Yaw", value: headPose.yaw, color: "#818cf8", desc: "left/right" },
                      { label: "Roll", value: headPose.roll, color: "#f59e0b", desc: "tilt" },
                    ].map(({ label, value, color, desc }) => (
                      <div key={label} className="text-center p-2 rounded-xl"
                        style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                        <div className="text-lg font-bold" style={{ color }}>{value.toFixed(0)}°</div>
                        <div className="text-[9px] text-[rgba(255,255,255,0.4)] font-semibold uppercase tracking-wide">{label}</div>
                        <div className="text-[8.5px] text-[rgba(255,255,255,0.2)]">{desc}</div>
                      </div>
                    ))}
                  </div>
                  <KVRow label="Frontal" value={headPose.is_frontal ? "Yes ✓" : "No"}
                    highlight={headPose.is_frontal ? "#00E5A8" : "#f87171"} />
                  <KVRow label="Extreme Pose" value={headPose.is_extreme ? "Suspicious" : "Normal"}
                    highlight={headPose.is_extreme ? "#f87171" : undefined} />
                  <KVRow label="Method" value={headPose.method} />
                </div>
              ) : (
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] py-2">
                  {scanning ? "Running MediaPipe solvePnP pose estimation…" : "Run a scan to estimate head pose"}
                </p>
              )}
            </ModuleCard>
          </div>
        </div>

        {/* ── RIGHT — Trust Score + Device ──────────────────────────── */}
        <div className="space-y-4">
          {/* NeoFace Trust Score */}
          <div className="rounded-2xl p-5"
            style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="flex items-center gap-2 mb-4">
              <ShieldCheck size={14} style={{ color: "#818cf8" }} />
              <span className="text-[13px] font-semibold text-white">NeoFace Trust Score</span>
              <span className="ml-auto text-[10px] text-[rgba(255,255,255,0.25)]">Personalized</span>
            </div>

            {riskScore ? (
              <div className="space-y-5">
                <div className="flex justify-center">
                  <TrustBadge score={riskScore.final_trust_score} decision={riskScore.decision} />
                </div>

                {/* Score bar */}
                <div>
                  <div className="flex justify-between text-[10px] text-[rgba(255,255,255,0.3)] mb-1.5">
                    <span>0</span>
                    <span className="text-[#f87171]">70 Reject</span>
                    <span className="text-[#f59e0b]">90 Step-Up</span>
                    <span className="text-[#00E5A8]">100</span>
                  </div>
                  <div className="h-2 rounded-full relative overflow-hidden"
                    style={{ background: "linear-gradient(90deg, rgba(248,113,113,0.3) 0%, rgba(245,158,11,0.3) 70%, rgba(0,229,168,0.3) 90%)" }}>
                    <motion.div
                      className="absolute top-0 bottom-0 w-2 rounded-full"
                      style={{ background: "white", boxShadow: "0 0 6px rgba(255,255,255,0.8)" }}
                      initial={{ left: "0%" }}
                      animate={{ left: `${Math.min(98, riskScore.final_trust_score)}%` }}
                      transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                    />
                  </div>
                </div>

                {/* Component scores */}
                <div className="space-y-1.5">
                  <p className="text-[10px] font-semibold text-[rgba(255,255,255,0.25)] uppercase tracking-wider mb-2">Component Scores</p>
                  {Object.entries(riskScore.component_scores).filter(([, v]) => v != null).map(([key, val]) => {
                    const labels: Record<string, string> = {
                      face_score: "Face Match", liveness_score: "Liveness",
                      deepfake_score: "Anti-Deepfake", behavior_score: "Behavior",
                      device_trust_score: "Device Trust", location_trust: "Location",
                      fingerprint_trust: "Fingerprint",
                    };
                    const v = val as number;
                    return (
                      <div key={key} className="flex items-center gap-2">
                        <span className="text-[10px] text-[rgba(255,255,255,0.35)] w-24 shrink-0">{labels[key] ?? key}</span>
                        <div className="flex-1 h-1 rounded-full bg-[rgba(255,255,255,0.05)]">
                          <motion.div className="h-full rounded-full"
                            style={{ background: v >= 80 ? "#00E5A8" : v >= 60 ? "#f59e0b" : "#f87171" }}
                            initial={{ width: 0 }}
                            animate={{ width: `${v}%` }}
                            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                          />
                        </div>
                        <span className="text-[10px] font-medium w-8 text-right"
                          style={{ color: v >= 80 ? "#00E5A8" : v >= 60 ? "#f59e0b" : "#f87171" }}>
                          {v.toFixed(0)}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Flags */}
                {riskScore.risk_flags.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-semibold text-[rgba(255,255,255,0.25)] uppercase tracking-wider">Risk Flags</p>
                    {riskScore.risk_flags.slice(0, 5).map(flag => (
                      <div key={flag} className="flex items-center gap-1.5 text-[10px]">
                        <AlertTriangle size={9} style={{ color: "#f59e0b" }} />
                        <span className="text-[rgba(255,255,255,0.4)]">{flag}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Explanation */}
                <div className="p-3 rounded-xl text-[10.5px] text-[rgba(255,255,255,0.35)] leading-relaxed"
                  style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}>
                  {riskScore.explanation}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 gap-3">
                <div className="w-16 h-16 rounded-full flex items-center justify-center"
                  style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.15)" }}>
                  <Target size={24} style={{ color: "rgba(99,102,241,0.5)" }} />
                </div>
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] text-center">
                  {scanning ? "Computing Trust Score…" : "Run a scan to generate your Trust Score"}
                </p>
              </div>
            )}
          </div>

          {/* Score legend */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { range: "90–100", label: "Approve", color: "#00E5A8", bg: "rgba(0,229,168,0.08)", border: "rgba(0,229,168,0.2)" },
              { range: "70–89", label: "Step-Up", color: "#f59e0b", bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.2)" },
              { range: "0–69", label: "Reject", color: "#f87171", bg: "rgba(248,113,113,0.08)", border: "rgba(248,113,113,0.2)" },
            ].map(({ range, label, color, bg, border }) => (
              <div key={label} className="text-center p-2.5 rounded-xl"
                style={{ background: bg, border: `1px solid ${border}` }}>
                <div className="text-[11px] font-bold" style={{ color }}>{range}</div>
                <div className="text-[9px] text-[rgba(255,255,255,0.3)] mt-0.5">{label}</div>
              </div>
            ))}
          </div>

          {/* Device Trust */}
          <ModuleCard title="Device Integrity" icon={Smartphone} color="#818cf8" status={deviceTrust ? (deviceTrust.device_trust >= 80 ? "pass" : "fail") : "idle"} collapsible>
            {deviceTrust ? (
              <div className="space-y-1.5">
                <div className="flex items-center gap-3 mb-2">
                  <ScoreRing score={deviceTrust.device_trust} size={56} color={deviceTrust.device_trust >= 80 ? "#818cf8" : "#f87171"} label="Device" />
                  <div className="flex-1 space-y-1">
                    <KVRow label="Platform" value="Web Browser" />
                    <KVRow label="Virtual Camera" value={deviceTrust.virtual_camera ? "Detected!" : "Clean"}
                      highlight={deviceTrust.virtual_camera ? "#f87171" : "#00E5A8"} />
                    <KVRow label="Automation" value={deviceTrust.automation_detected ? "Detected!" : "Clean"}
                      highlight={deviceTrust.automation_detected ? "#f87171" : "#00E5A8"} />
                  </div>
                </div>
                {deviceTrust.risk_flags.length > 0 && (
                  <div className="pt-2 border-t border-[rgba(255,255,255,0.06)]">
                    {deviceTrust.risk_flags.slice(0, 3).map(f => (
                      <div key={f} className="flex items-center gap-1.5 text-[10px] py-0.5">
                        <AlertTriangle size={9} style={{ color: "#f59e0b" }} />
                        <span className="text-[rgba(255,255,255,0.4)]">{f}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-[11px] text-[rgba(255,255,255,0.2)] py-1">
                Assessing device integrity…
              </p>
            )}
          </ModuleCard>

          {/* How it works */}
          <div className="rounded-2xl p-4 space-y-2.5"
            style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="flex items-center gap-2 mb-1">
              <Info size={12} style={{ color: "rgba(255,255,255,0.3)" }} />
              <span className="text-[11px] font-semibold text-[rgba(255,255,255,0.4)]">How Trust Score Works</span>
            </div>
            {[
              { weight: "25%", label: "Face Match (your enrolled data)", color: "#00E5A8" },
              { weight: "20%", label: "Liveness Score", color: "#00C2FF" },
              { weight: "15%", label: "Anti-Deepfake", color: "#f87171" },
              { weight: "15%", label: "Behavioral (head pose)", color: "#f59e0b" },
              { weight: "15%", label: "Device Trust", color: "#818cf8" },
              { weight: "10%", label: "Location + Fingerprint", color: "#9ca3af" },
            ].map(({ weight, label, color }) => (
              <div key={label} className="flex items-center gap-2 text-[10px]">
                <span className="font-bold w-8 text-right" style={{ color }}>{weight}</span>
                <span className="text-[rgba(255,255,255,0.3)]">{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes scanDown {
          0% { top: 0; }
          100% { top: 100%; }
        }
      `}</style>
    </div>
  );
}
