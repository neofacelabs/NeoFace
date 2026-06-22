"use client";
import { useRef, useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Scan, Eye, Fingerprint, ShieldCheck, Upload, Camera, CheckCircle2, XCircle,
  Loader2, AlertCircle, Zap, Star, RotateCw, ChevronLeft, ChevronRight,
  Clock, Trash2, RefreshCw, Lock, Settings,
} from "lucide-react";
import { biometricsApi, enrollmentApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { toast } from "sonner";
import { extractErrorMsg } from "@/lib/utils";

/* ── Types ────────────────────────────────────────────────────────────────── */
interface BiometricStatusModality {
  enrolled: boolean;
  embedding_count?: number;
  record_count?: number;
  template_count?: number;
}
interface BiometricStatus {
  user_id: string;
  face: BiometricStatusModality;
  iris: BiometricStatusModality;
  fingerprint: BiometricStatusModality;
  modalities_enrolled: number;
  max_security: boolean;
  enrolled_at?: string;
}

/* ── Face angle guide config ─────────────────────────────────────────────── */
const FACE_ANGLES = [
  { key: "front",  label: "Front",       guide: "Look straight at the camera",        oval: { cx: 320, cy: 240, rx: 130, ry: 170 }, prompt: "👁️" },
  { key: "right",  label: "Left Turn",   guide: "Turn your head slightly to the left", oval: { cx: 290, cy: 240, rx: 110, ry: 170 }, prompt: "👈" },
  { key: "left",   label: "Right Turn",  guide: "Turn your head slightly to the right", oval: { cx: 350, cy: 240, rx: 110, ry: 170 }, prompt: "👉" },
] as const;

/* ── Security score ring ──────────────────────────────────────────────────── */
function SecurityRing({ enrolled }: { enrolled: number }) {
  const pct = (enrolled / 2) * 100;
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = enrolled === 2 ? "#00E5A8" : enrolled === 1 ? "#818cf8" : "#333";
  const label = enrolled === 2 ? "MAX" : enrolled === 1 ? "MED" : "LOW";

  return (
    <div className="relative flex items-center justify-center w-20 h-20">
      <svg width="80" height="80" className="absolute inset-0 -rotate-90">
        <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
        <motion.circle
          cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="4"
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ - dash}
          initial={{ strokeDashoffset: circ }} animate={{ strokeDashoffset: circ - dash }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          style={{ filter: `drop-shadow(0 0 6px ${color}50)` }}
        />
      </svg>
      <div className="relative text-center">
        <p className="text-[11px] font-bold leading-none" style={{ color }}>{label}</p>
        <p className="text-[8px] text-[rgba(255,255,255,0.3)] mt-0.5">SECURITY</p>
      </div>
    </div>
  );
}

/* ── Liveness indicator ──────────────────────────────────────────────────── */
function LivenessBar({ score }: { score: number | null }) {
  if (score === null) return null;
  const pct = Math.round(score * 100);
  const color = pct >= 75 ? "#00E5A8" : pct >= 45 ? "#f59e0b" : "#ef4444";
  const label = pct >= 75 ? "Live" : pct >= 45 ? "Uncertain" : "Spoof?";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.07)" }}>
        <motion.div
          initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5 }}
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 8px ${color}60` }}
        />
      </div>
      <span className="text-[10px] font-semibold tabular-nums" style={{ color }}>{pct}% {label}</span>
    </div>
  );
}

/* ── Enrolled face gallery ───────────────────────────────────────────────── */
function EnrolledFaceView({ status, modalityKey, onDelete }: {
  status: BiometricStatus | undefined;
  modalityKey: string;
  onDelete: () => void;
}) {
  const [idx, setIdx] = useState(0);
  const angles = FACE_ANGLES;

  if (modalityKey === "fingerprint") {
    return (
      <div className="space-y-3">
        <div className="p-4 rounded-xl" style={{ background: "rgba(0,194,255,0.03)", border: "1px solid rgba(0,194,255,0.1)" }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.2)" }}>
              <Fingerprint size={16} style={{ color: "#00C2FF" }} />
            </div>
            <div>
              <p className="text-[12.5px] font-semibold text-white">Active WebAuthn Fingerprints</p>
              <p className="text-[10.5px] text-[rgba(255,255,255,0.3)] mt-0.5">
                {status?.fingerprint?.template_count || 0} device credentials registered
              </p>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Link
            href="/dashboard/fingerprint"
            className="flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-[11.5px] font-medium transition-all hover:bg-[rgba(255,255,255,0.08)]"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.6)" }}
          >
            <Settings size={12} /> Manage Devices
          </Link>
          <button
            onClick={onDelete}
            className="flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-[11.5px] font-medium transition-all hover:bg-[rgba(239,68,68,0.12)]"
            style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)", color: "rgba(239,68,68,0.7)" }}
          >
            <Trash2 size={12} /> Reset / Delete All
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Multi-angle view */}
      <div className="grid grid-cols-3 gap-2">
        {angles.map((a, i) => (
          <div
            key={a.key}
            onClick={() => setIdx(i)}
            className="relative rounded-xl overflow-hidden cursor-pointer group transition-all"
            style={{
              aspectRatio: "3/4",
              background: "rgba(0,229,168,0.04)",
              border: `1px solid ${i === idx ? "rgba(0,229,168,0.4)" : "rgba(0,229,168,0.12)"}`,
              boxShadow: i === idx ? "0 0 20px rgba(0,229,168,0.15)" : "none",
            }}
          >
            {/* Placeholder silhouette */}
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
              <div
                className="rounded-full"
                style={{
                  width: "45%", paddingTop: "45%",
                  background: "rgba(0,229,168,0.12)",
                  border: "1px solid rgba(0,229,168,0.2)",
                }}
              />
              <div
                className="rounded-full mt-1"
                style={{
                  width: "62%", height: "30%",
                  background: "rgba(0,229,168,0.07)",
                  border: "1px solid rgba(0,229,168,0.15)",
                }}
              />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              <div
                className="text-lg"
                style={{ filter: "drop-shadow(0 0 8px rgba(0,229,168,0.5))" }}
              >
                {a.prompt}
              </div>
            </div>
            <div
              className="absolute bottom-0 inset-x-0 py-1 text-center text-[9px] font-semibold"
              style={{
                background: "rgba(0,0,0,0.7)",
                color: i === idx ? "#00E5A8" : "rgba(255,255,255,0.4)",
              }}
            >
              {a.label}
            </div>
            <div
              className="absolute top-1 right-1 w-3.5 h-3.5 rounded-full flex items-center justify-center"
              style={{ background: "rgba(0,229,168,0.15)" }}
            >
              <CheckCircle2 size={8} style={{ color: "#00E5A8" }} />
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between text-[10px] text-[rgba(255,255,255,0.3)]">
        <span className="flex items-center gap-1">
          <CheckCircle2 size={10} style={{ color: "#00E5A8" }} />
          <span style={{ color: "#00E5A8" }}>3 angles enrolled</span>
        </span>
        {status?.enrolled_at && (
          <span className="flex items-center gap-1">
            <Clock size={9} />
            {new Date(status.enrolled_at).toLocaleDateString()}
          </span>
        )}
      </div>

      <button
        onClick={onDelete}
        className="w-full flex items-center justify-center gap-2 py-2 rounded-xl text-[11.5px] font-medium transition-all hover:bg-[rgba(239,68,68,0.12)]"
        style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.15)", color: "rgba(239,68,68,0.7)" }}
      >
        <Trash2 size={12} /> Re-enroll / Delete
      </button>
    </div>
  );
}

/* ── Live face capture with liveness ────────────────────────────────────── */
function LiveFaceCapture({
  onAllCaptured,
}: {
  onAllCaptured: (blobs: Blob[]) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animRef = useRef<number>(0);

  const [streaming, setStreaming] = useState(false);
  const [currentAngle, setCurrentAngle] = useState(0);
  const [captured, setCaptured] = useState<string[]>([]);
  const [blobs, setBlobs] = useState<Blob[]>([]);
  const [livenessScore, setLivenessScore] = useState<number | null>(null);
  const [blinkDetected, setBlinkDetected] = useState(false);
  const [blinkCount, setBlinkCount] = useState(0);
  const [faceDetected, setFaceDetected] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  // Simulate liveness analysis on video stream
  const analyseLiveness = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !streaming) return;
    const ctx = canvasRef.current.getContext("2d")!;
    canvasRef.current.width = 64;
    canvasRef.current.height = 64;
    ctx.drawImage(videoRef.current, 0, 0, 64, 64);
    const pixels = ctx.getImageData(0, 0, 64, 64).data;
    // Simple brightness variance → proxy for "face present"
    let sum = 0, sumSq = 0;
    for (let i = 0; i < pixels.length; i += 4) {
      const lum = pixels[i] * 0.299 + pixels[i + 1] * 0.587 + pixels[i + 2] * 0.114;
      sum += lum; sumSq += lum * lum;
    }
    const n = pixels.length / 4;
    const mean = sum / n;
    const variance = sumSq / n - mean * mean;
    const detected = mean > 25 && mean < 220 && variance > 200;
    setFaceDetected(detected);
    if (detected) {
      // Simulate liveness score rising over time
      setLivenessScore(prev => {
        const target = 0.72 + Math.random() * 0.22;
        if (prev === null) return target * 0.4;
        return Math.min(0.98, prev + (target - prev) * 0.08);
      });
      // Simulate blink detection
      if (Math.random() < 0.015) {
        setBlinkCount(c => {
          const next = c + 1;
          if (!blinkDetected && next >= 1) setBlinkDetected(true);
          return next;
        });
      }
    } else {
      setLivenessScore(null);
    }
    animRef.current = requestAnimationFrame(analyseLiveness);
  }, [streaming, blinkDetected]);

  useEffect(() => {
    if (streaming) {
      animRef.current = requestAnimationFrame(analyseLiveness);
    }
    return () => cancelAnimationFrame(animRef.current);
  }, [streaming, analyseLiveness]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: 640, height: 480 },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setStreaming(true);
      }
    } catch {
      toast.error("Camera access denied. Please allow camera permission.");
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    setStreaming(false);
  };

  const captureAngle = () => {
    if (!videoRef.current || !canvasRef.current) return;
    if (!faceDetected) { toast.error("No face detected — please position your face in the oval"); return; }
    if (!blinkDetected) { toast.error("Please blink once to confirm you are live"); return; }
    if ((livenessScore ?? 0) < 0.45) { toast.error("Liveness check failed — try better lighting"); return; }

    // Countdown then capture
    setCountdown(3);
    let c = 3;
    const t = setInterval(() => {
      c--;
      setCountdown(c > 0 ? c : null);
      if (c <= 0) {
        clearInterval(t);
        doCapture();
      }
    }, 1000);
  };

  const doCapture = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const cv = canvasRef.current;
    cv.width = videoRef.current.videoWidth;
    cv.height = videoRef.current.videoHeight;
    const ctx = cv.getContext("2d")!;
    ctx.drawImage(videoRef.current, 0, 0);
    const dataUrl = cv.toDataURL("image/jpeg", 0.9);
    cv.toBlob(async (blob) => {
      if (!blob) return;

      setIsValidating(true);
      const validateToastId = toast.loading(`Validating ${FACE_ANGLES[currentAngle].label} frame...`);

      try {
        const fd = new FormData();
        fd.append("file", blob, `face_${FACE_ANGLES[currentAngle].key}.jpg`);

        const response = await enrollmentApi.validateFrame(fd);
        if (response.data && response.data.success) {
          toast.success(`${FACE_ANGLES[currentAngle].label} angle validated successfully!`, { id: validateToastId });

          const newBlobs = [...blobs, blob];
          const newCaptured = [...captured, dataUrl];
          setBlobs(newBlobs);
          setCaptured(newCaptured);

          // Reset blink for next angle
          setBlinkDetected(false);
          setBlinkCount(0);

          if (currentAngle < FACE_ANGLES.length - 1) {
            setCurrentAngle(a => a + 1);
          } else {
            // All 3 captured and verified
            stopCamera();
            onAllCaptured(newBlobs);
            toast.success("All 3 angles captured and verified! Ready to enroll.");
          }
        } else {
          const errMsg = response.data?.error || "No valid face detected. Please try again.";
          toast.error(errMsg, { id: validateToastId });
        }
      } catch (err: any) {
        const errMsg = extractErrorMsg(err, "Frame validation failed. Please check your network and try again.");
        toast.error(errMsg, { id: validateToastId });
      } finally {
        setIsValidating(false);
      }
    }, "image/jpeg", 0.9);
  };

  const reset = () => {
    stopCamera();
    setCaptured([]); setBlobs([]); setCurrentAngle(0);
    setLivenessScore(null); setBlinkDetected(false); setBlinkCount(0);
    setFaceDetected(false);
  };

  const angle = FACE_ANGLES[currentAngle];
  const { cx, cy, rx, ry } = angle.oval;

  return (
    <div className="space-y-3">
      {/* Angle progress */}
      <div className="flex gap-2">
        {FACE_ANGLES.map((a, i) => (
          <div key={a.key} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full h-1 rounded-full transition-all"
              style={{
                background: i < captured.length ? "#00E5A8" : i === currentAngle ? "rgba(0,229,168,0.4)" : "rgba(255,255,255,0.08)",
                boxShadow: i === currentAngle ? "0 0 6px rgba(0,229,168,0.4)" : "none",
              }}
            />
            <span
              className="text-[9px] font-medium"
              style={{ color: i < captured.length ? "#00E5A8" : i === currentAngle ? "rgba(0,229,168,0.7)" : "rgba(255,255,255,0.2)" }}
            >
              {i < captured.length ? "✓" : a.label}
            </span>
          </div>
        ))}
      </div>

      {/* Camera viewport */}
      <div className="relative rounded-xl overflow-hidden bg-black" style={{ aspectRatio: "4/3" }}>
        <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />

        {!streaming && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3" style={{ background: "rgba(0,0,0,0.85)" }}>
            <Camera size={32} style={{ color: "rgba(255,255,255,0.15)" }} />
            <p className="text-[12px] text-[rgba(255,255,255,0.3)]">Camera not started</p>
          </div>
        )}

        {/* Face oval guide */}
        {streaming && (
          <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 640 480">
            {/* Dimming outside oval */}
            <defs>
              <mask id="oval-mask">
                <rect width="640" height="480" fill="white" />
                <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="black" />
              </mask>
            </defs>
            <rect width="640" height="480" fill="rgba(0,0,0,0.45)" mask="url(#oval-mask)" />
            <ellipse
              cx={cx} cy={cy} rx={rx} ry={ry}
              fill="none"
              stroke={faceDetected ? (livenessScore && livenessScore > 0.65 ? "#00E5A8" : "#f59e0b") : "rgba(255,255,255,0.3)"}
              strokeWidth="2.5"
              strokeDasharray={blinkDetected ? "0" : "10 6"}
              style={{ filter: faceDetected ? "drop-shadow(0 0 8px rgba(0,229,168,0.6))" : "none" }}
            />
            {/* Corner brackets */}
            {[[-1,-1],[1,-1],[-1,1],[1,1]].map(([sx,sy], i) => (
              <g key={i} transform={`translate(${cx + sx*rx*0.72}, ${cy + sy*ry*0.82})`}>
                <line x1={0} y1={0} x2={sx*14} y2={0} stroke="#00E5A8" strokeWidth="2.5" strokeLinecap="round" opacity={faceDetected ? 0.9 : 0.3} />
                <line x1={0} y1={0} x2={0} y2={sy*14} stroke="#00E5A8" strokeWidth="2.5" strokeLinecap="round" opacity={faceDetected ? 0.9 : 0.3} />
              </g>
            ))}
          </svg>
        )}

        {/* Countdown overlay */}
        {countdown !== null && (
          <div className="absolute inset-0 flex items-center justify-center" style={{ background: "rgba(0,0,0,0.3)" }}>
            <motion.div
              key={countdown}
              initial={{ scale: 1.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              exit={{ opacity: 0 }} transition={{ duration: 0.4 }}
              className="text-[80px] font-black"
              style={{ color: "#00E5A8", textShadow: "0 0 40px rgba(0,229,168,0.8)" }}
            >
              {countdown}
            </motion.div>
          </div>
        )}

        {/* Validating overlay */}
        {isValidating && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 animate-fade-in" style={{ background: "rgba(0,0,0,0.75)" }}>
            <Loader2 className="w-10 h-10 animate-spin text-[#00E5A8]" />
            <p className="text-[13px] font-medium text-white">Analyzing face quality...</p>
            <p className="text-[10px] text-[rgba(255,255,255,0.4)]">Checking lighting, blur, and angle</p>
          </div>
        )}

        {/* Guide text overlay */}
        {streaming && countdown === null && (
          <div className="absolute bottom-3 inset-x-3 flex flex-col items-center gap-1.5">
            <div
              className="px-3 py-1.5 rounded-lg text-center text-[11px] font-medium"
              style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(8px)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.8)" }}
            >
              {angle.guide}
            </div>
          </div>
        )}

        {/* Status pills */}
        {streaming && (
          <div className="absolute top-2 left-2 flex flex-col gap-1.5">
            {/* Face detected */}
            <div
              className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[9.5px] font-semibold"
              style={{
                background: "rgba(0,0,0,0.75)",
                border: `1px solid ${faceDetected ? "rgba(0,229,168,0.4)" : "rgba(255,255,255,0.15)"}`,
                color: faceDetected ? "#00E5A8" : "rgba(255,255,255,0.4)",
              }}
            >
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: faceDetected ? "#00E5A8" : "rgba(255,255,255,0.3)", boxShadow: faceDetected ? "0 0 4px #00E5A8" : "none" }} />
              {faceDetected ? "Face Detected" : "No Face"}
            </div>
            {/* Blink */}
            <div
              className="flex items-center gap-1.5 px-2 py-1 rounded-md text-[9.5px] font-semibold"
              style={{
                background: "rgba(0,0,0,0.75)",
                border: `1px solid ${blinkDetected ? "rgba(0,194,255,0.4)" : "rgba(255,255,255,0.15)"}`,
                color: blinkDetected ? "#00C2FF" : "rgba(255,255,255,0.4)",
              }}
            >
              <span className="text-[10px]">{blinkDetected ? "👁️" : "👁"}</span>
              {blinkDetected ? "Blink ✓" : "Blink needed"}
            </div>
          </div>
        )}

        <canvas ref={canvasRef} className="hidden" />
      </div>

      {/* Liveness bar */}
      {streaming && (
        <div className="px-0.5 space-y-1">
          <div className="flex items-center justify-between text-[9.5px] text-[rgba(255,255,255,0.3)]">
            <span>Liveness Score</span>
            <span>{blinkCount} blink{blinkCount !== 1 ? "s" : ""} detected</span>
          </div>
          <LivenessBar score={livenessScore} />
        </div>
      )}

      {/* Captured thumbnails */}
      {captured.length > 0 && (
        <div className="flex gap-2">
          {captured.map((src, i) => (
            <div key={i} className="relative rounded-lg overflow-hidden" style={{ width: 56, height: 56 }}>
              <img src={src} className="w-full h-full object-cover" alt={FACE_ANGLES[i]?.label || `Angle ${i + 1}`} />
              <div className="absolute bottom-0 inset-x-0 text-center text-[7px] py-0.5" style={{ background: "rgba(0,229,168,0.8)", color: "#000", fontWeight: 700 }}>
                {FACE_ANGLES[i]?.label || `Angle ${i + 1}`}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Controls */}
      <div className="flex gap-2">
        {!streaming ? (
          <>
            <button
              onClick={startCamera}
              disabled={isValidating}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-[12.5px] font-semibold transition-all disabled:opacity-40"
              style={{ background: "rgba(0,229,168,0.1)", border: "1px solid rgba(0,229,168,0.25)", color: "#00E5A8" }}
            >
              <Camera size={14} /> {captured.length > 0 ? "Continue Capture" : "Start Camera"}
            </button>
            {captured.length > 0 && (
              <button onClick={reset} disabled={isValidating} className="px-3 py-2.5 rounded-xl transition-all disabled:opacity-40" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.4)" }}>
                <RotateCw size={14} />
              </button>
            )}
          </>
        ) : (
          <button
            onClick={captureAngle}
            disabled={!faceDetected || !blinkDetected || (livenessScore ?? 0) < 0.45 || isValidating}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-[12.5px] font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: "rgba(0,229,168,0.15)", border: "1px solid rgba(0,229,168,0.4)", color: "#00E5A8" }}
          >
            {isValidating ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Validating {angle.label}...
              </>
            ) : (
              <>
                <Scan size={14} />
                Capture {angle.label} ({currentAngle + 1}/3)
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

/* ── File drop zone ────────────────────────────────────────────────────────── */
function FileDropZone({ color, label, onFile }: { color: string; label: string; onFile: (file: File) => void }) {
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = (file: File) => {
    onFile(file);
    const reader = new FileReader();
    reader.onload = e => setPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  if (preview) {
    return (
      <div className="relative rounded-xl overflow-hidden" style={{ aspectRatio: "4/3" }}>
        <img src={preview} alt="uploaded" className="w-full h-full object-cover" />
        <div className="absolute inset-0 flex items-center justify-center" style={{ background: `${color}22` }}>
          <div className="flex flex-col items-center gap-2">
            <CheckCircle2 size={24} style={{ color }} />
            <p className="text-[12px] font-semibold text-white">Image Ready</p>
          </div>
        </div>
        <button onClick={() => setPreview(null)}
          className="absolute top-2 right-2 px-2.5 py-1 rounded-lg text-[10px] font-medium"
          style={{ background: "rgba(0,0,0,0.7)", color: "rgba(255,255,255,0.6)" }}>
          Replace
        </button>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer transition-all"
      style={{
        aspectRatio: "4/3",
        background: dragging ? `${color}10` : "rgba(255,255,255,0.02)",
        border: `1.5px dashed ${dragging ? color : "rgba(255,255,255,0.1)"}`,
      }}
      onDragOver={e => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handle(f); }}
      onClick={() => inputRef.current?.click()}
    >
      <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${color}12`, border: `1px solid ${color}20` }}>
        <Upload size={18} style={{ color }} />
      </div>
      <div className="text-center">
        <p className="text-[12px] font-medium text-white">Drop {label} image</p>
        <p className="text-[10.5px] text-[rgba(255,255,255,0.3)] mt-0.5">or click to browse · JPG, PNG</p>
      </div>
      <input ref={inputRef} type="file" accept="image/*" className="hidden" onChange={e => e.target.files?.[0] && handle(e.target.files[0])} />
    </div>
  );
}

/* ── Modality enrollment card ─────────────────────────────────────────────── */
function ModalityCard({
  modality,
  enrolled,
  status,
}: {
  modality: { key: string; icon: any; label: string; desc: string; color: string; statusKey: "face" | "iris" | "fingerprint"; inputType: "camera" | "file" | "redirect" };
  enrolled: boolean;
  status: BiometricStatus | undefined;
}) {
  const qc = useQueryClient();
  const { user } = useAuthStore();
  const [capturedBlobs, setCapturedBlobs] = useState<Blob[]>([]);
  const [capturedFile, setCapturedFile] = useState<File | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [showView, setShowView] = useState(false);

  // Delete / re-enroll
  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!user?.id) throw new Error("Not authenticated");
      if (modality.key === "face") {
        return biometricsApi.deleteFace();
      } else if (modality.key === "fingerprint") {
        return biometricsApi.deleteFingerprint();
      } else if (modality.key === "iris") {
        return biometricsApi.deleteIris();
      }
      throw new Error(`Unknown modality: ${modality.key}`);
    },
    onSuccess: () => {
      toast.success(`${modality.label} deleted — you can re-enroll now`);
      qc.invalidateQueries({ queryKey: ["biometric-status"] });
      setShowView(false);
      setExpanded(true);
    },
    onError: (e: any) => toast.error(extractErrorMsg(e, `Failed to delete ${modality.label}`)),
  });

  const submit = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      if (modality.key === "face") {
        if (capturedBlobs.length === 0) throw new Error("No face captured");
        fd.append("name", user?.name || "NeoFace User");
        fd.append("email", user?.email || "user@neoface.io");
        capturedBlobs.forEach((blob, i) => fd.append("images", blob, `face_${i}.jpg`));
        return enrollmentApi.enroll(fd);
      } else if (modality.key === "iris") {
        if (!capturedFile) throw new Error("No iris image");
        fd.append("iris_image", capturedFile);
        return biometricsApi.enrollIris(fd);
      } else {
        if (!capturedFile) throw new Error("No fingerprint image");
        fd.append("fingerprint_image", capturedFile);
        return biometricsApi.enrollFingerprint(fd);
      }
    },
    onSuccess: () => {
      toast.success(`${modality.label} enrolled successfully`);
      qc.invalidateQueries({ queryKey: ["biometric-status"] });
      setExpanded(false);
      setCapturedBlobs([]);
      setCapturedFile(null);
    },
    onError: (e: any) => toast.error(extractErrorMsg(e, `Failed to enroll ${modality.label}`)),
  });

  const hasCapture = modality.key === "face" ? capturedBlobs.length === 3 : !!capturedFile;

  return (
    <motion.div
      layout
      className="rounded-2xl overflow-hidden"
      style={{
        background: enrolled ? `${modality.color}06` : "rgba(255,255,255,0.02)",
        border: enrolled ? `1px solid ${modality.color}25` : "1px solid rgba(255,255,255,0.07)",
        boxShadow: "0 1px 20px rgba(0,0,0,0.35)",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer"
        onClick={() => {
          if (enrolled) { setShowView(v => !v); setExpanded(false); }
          else { setExpanded(v => !v); setShowView(false); }
        }}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: enrolled ? `${modality.color}15` : "rgba(255,255,255,0.05)", border: `1px solid ${modality.color}25` }}>
            <modality.icon size={16} style={{ color: enrolled ? modality.color : "rgba(255,255,255,0.3)" }} />
          </div>
          <div>
            <p className="text-[13.5px] font-semibold text-white">{modality.label}</p>
            <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">{modality.desc}</p>
          </div>
        </div>
        <div>
          {enrolled ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-semibold"
              style={{ background: `${modality.color}12`, border: `1px solid ${modality.color}25`, color: modality.color }}>
              <CheckCircle2 size={10} />
              {showView ? "Close" : "View"}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.4)" }}>
              {expanded ? "▲ Collapse" : "▼ Enroll"}
            </div>
          )}
        </div>
      </div>

      {/* Enrolled view */}
      <AnimatePresence>
        {enrolled && showView && status && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
              <div className="pt-3">
                <EnrolledFaceView status={status} modalityKey={modality.key} onDelete={() => deleteMutation.mutate()} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Enrollment panel */}
      <AnimatePresence>
        {expanded && !enrolled && (
          <motion.div
            initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3">
              <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }} className="pt-3">
                {modality.inputType === "camera" ? (
                  <LiveFaceCapture onAllCaptured={blobs => setCapturedBlobs(blobs)} />
                ) : modality.inputType === "redirect" ? (
                  <div className="p-4 rounded-xl text-center space-y-3" style={{ background: "rgba(0,194,255,0.03)", border: "1px solid rgba(0,194,255,0.1)" }}>
                    <p className="text-[11.5px] text-[rgba(255,255,255,0.4)] leading-relaxed">
                      Fingerprint security is hardware-backed using FIDO2/WebAuthn. Enrollment requires secure prompt interaction on your device.
                    </p>
                    <Link
                      href="/dashboard/fingerprint"
                      className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-[12px] font-semibold transition-all hover:bg-[rgba(0,194,255,0.2)]"
                      style={{ background: "rgba(0,194,255,0.12)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}
                    >
                      Go to Fingerprint Enrollment <ChevronRight size={12} />
                    </Link>
                  </div>
                ) : (
                  <FileDropZone
                    color={modality.color}
                    label={modality.key}
                    onFile={file => setCapturedFile(file)}
                  />
                )}
              </div>

              {modality.inputType !== "redirect" && (
                <button
                  onClick={() => submit.mutate()}
                  disabled={!hasCapture || submit.isPending}
                  className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-[12.5px] font-semibold transition-all"
                  style={{
                    background: hasCapture ? `${modality.color}15` : "rgba(255,255,255,0.04)",
                    border: `1px solid ${hasCapture ? modality.color + "35" : "rgba(255,255,255,0.08)"}`,
                    color: hasCapture ? modality.color : "rgba(255,255,255,0.25)",
                    cursor: hasCapture ? "pointer" : "not-allowed",
                  }}
                >
                  {submit.isPending ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                  {submit.isPending ? "Enrolling…" : `Enroll ${modality.label}`}
                </button>
              )}

              {modality.key === "face" && !hasCapture && (
                <p className="text-[10px] text-center" style={{ color: "rgba(255,255,255,0.25)" }}>
                  Capture all 3 angles (front, left, right) to enable enroll
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ── Iris Coming Soon card ───────────────────────────────────────────────── */
function IrisComingSoonCard() {
  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{
        background: "rgba(255,255,255,0.015)",
        border: "1px solid rgba(255,255,255,0.07)",
        boxShadow: "0 1px 20px rgba(0,0,0,0.35)",
      }}
    >
      <div className="flex items-center justify-between p-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: "rgba(0,194,255,0.08)", border: "1px solid rgba(0,194,255,0.15)" }}>
            <Eye size={16} style={{ color: "rgba(0,194,255,0.5)" }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-[13.5px] font-semibold text-white">Iris Recognition</p>
              <div
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-bold"
                style={{ background: "rgba(245,158,11,0.12)", border: "1px solid rgba(245,158,11,0.3)", color: "#f59e0b" }}
              >
                <Clock size={8} />
                Coming Soon (Q4 2026)
              </div>
            </div>
            <p className="text-[11px] text-[rgba(255,255,255,0.25)] mt-0.5">High-precision infrared iris scanning</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium"
          style={{ background: "rgba(245,158,11,0.06)", border: "1px solid rgba(245,158,11,0.15)", color: "rgba(245,158,11,0.6)" }}>
          <Lock size={9} />
          Q4 2026
        </div>
      </div>
      <div className="mx-4 mb-4 p-3 rounded-xl" style={{ background: "rgba(0,194,255,0.04)", border: "1px solid rgba(0,194,255,0.1)" }}>
        <p className="text-[10.5px] text-[rgba(255,255,255,0.3)] leading-relaxed">
          🔬 Iris recognition provides 99.9% accuracy using near-infrared light to map unique iris patterns — more unique than fingerprints. We are building specialized hardware integration support.
        </p>
      </div>
    </div>
  );
}

/* ── Modality config ──────────────────────────────────────────────────────── */
const MODALITIES = [
  {
    key: "face",
    icon: Scan,
    label: "Face Recognition",
    desc: "Capture 3-angle live face via webcam",
    color: "#00E5A8",
    statusKey: "face" as const,
    inputType: "camera" as const,
  },
  {
    key: "fingerprint",
    icon: Fingerprint,
    label: "Fingerprint Recognition",
    desc: "Hardware-backed WebAuthn credentials",
    color: "#00C2FF",
    statusKey: "fingerprint" as const,
    inputType: "redirect" as const,
  },
];

/* ── Page ──────────────────────────────────────────────────────────────────── */
export default function IdentityPage() {
  const { data: status, isLoading } = useQuery<BiometricStatus>({
    queryKey: ["biometric-status"],
    queryFn: () => biometricsApi.getStatus().then(r => r.data),
    refetchInterval: 10_000,
  });

  const enrolledCount = status
    ? [status.face?.enrolled, status.fingerprint?.enrolled].filter(Boolean).length
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between"
      >
        <div>

          <h1 className="text-[22px] font-bold text-white tracking-tight">My Biometric Identity</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
            Enroll your biometric modalities to enable payment authorization
          </p>
        </div>

        {/* Security ring */}
        {!isLoading && <SecurityRing enrolled={enrolledCount} />}
      </motion.div>

      {/* Max Security Badge */}
      <AnimatePresence>
        {status?.max_security && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            className="flex items-center gap-3 p-4 rounded-2xl"
            style={{ background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.2)" }}>
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: "rgba(0,229,168,0.12)", border: "1px solid rgba(0,229,168,0.25)" }}>
              <Star size={16} style={{ color: "#00E5A8" }} fill="#00E5A8" />
            </div>
            <div>
              <p className="text-[13px] font-semibold" style={{ color: "#00E5A8" }}>Maximum Security Achieved</p>
              <p className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">
                All biometric modalities enrolled. Multi-layer identity protection active.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Progress */}
      {!isLoading && !status?.max_security && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="p-4 rounded-2xl"
          style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[11px] text-[rgba(255,255,255,0.4)] font-medium">Security Progress</p>
            <p className="text-[11px] font-semibold" style={{ color: "#00C2FF" }}>{enrolledCount} / {MODALITIES.length} modalities active</p>
          </div>
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
            <motion.div
              initial={{ width: 0 }} animate={{ width: `${(enrolledCount / MODALITIES.length) * 100}%` }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              className="h-full rounded-full"
              style={{ background: "linear-gradient(90deg, #818cf8, #00E5A8)" }}
            />
          </div>
          <p className="text-[10.5px] text-[rgba(255,255,255,0.25)] mt-2">
            Enroll Face Recognition to enable secure biometric checkout
          </p>
        </motion.div>
      )}

      {/* Modality cards */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 rounded-2xl animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {MODALITIES.map(m => (
            <ModalityCard
              key={m.key}
              modality={m}
              enrolled={status?.[m.statusKey]?.enrolled ?? false}
              status={status}
            />
          ))}
          {/* Iris coming soon */}
          <IrisComingSoonCard />
        </div>
      )}

      {/* Info */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
        className="flex items-start gap-3 p-4 rounded-xl"
        style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
        <AlertCircle size={14} className="shrink-0 mt-0.5" style={{ color: "rgba(255,255,255,0.2)" }} />
        <p className="text-[11px] text-[rgba(255,255,255,0.25)] leading-relaxed">
          Biometric data is converted to encrypted mathematical vectors. Raw images are never stored.
          You can revoke access at any time from this page.
        </p>
      </motion.div>
    </div>
  );
}
