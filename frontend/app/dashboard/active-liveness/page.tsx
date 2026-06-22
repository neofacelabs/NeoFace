"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Eye, CheckCircle2, XCircle, RefreshCw, Loader2,
  ShieldCheck, ChevronRight, Zap, Target, Clock,
} from "lucide-react";
import { toast } from "sonner";
import { livenessApi } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Challenge {
  challenge_id: string;
  challenge_type: string;
  steps: string[];
  descriptions: string[];
  difficulty: string;
  nonce: string;
  expires_in_seconds: number;
}

interface VerifyResult {
  challenge_completed: boolean;
  challenge_type: string;
  steps_completed: string[];
  steps_pending: string[];
  confidence: number;
  inference_ms: number;
  failure_reason?: string;
}

// ── Action description map ────────────────────────────────────────────────────
const ACTION_ICONS: Record<string, string> = {
  blink:          "👁️",
  smile:          "😊",
  open_mouth:     "😮",
  turn_left:      "⬅️",
  turn_right:     "➡️",
  raise_eyebrows: "🤨",
  look_up:        "⬆️",
  look_down:      "⬇️",
};

const DIFFICULTY_COLOR: Record<string, string> = {
  easy:   "#00E5A8",
  medium: "#f59e0b",
  hard:   "#f87171",
};

// ── Step indicator ────────────────────────────────────────────────────────────
function StepPill({ action, status }: { action: string; status: "pending" | "done" | "active" }) {
  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-xl text-[12px] font-medium transition-all",
        status === "done"
          ? "bg-[rgba(0,229,168,0.12)] border border-[rgba(0,229,168,0.25)] text-[#00E5A8]"
          : status === "active"
          ? "bg-[rgba(99,102,241,0.15)] border border-[rgba(99,102,241,0.4)] text-white"
          : "bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] text-[rgba(255,255,255,0.3)]"
      )}
    >
      <span className="text-base">{ACTION_ICONS[action] ?? "🎯"}</span>
      <span className="capitalize">{action.replace("_", " ")}</span>
      {status === "done" && <CheckCircle2 size={12} />}
      {status === "active" && <motion.div animate={{ scale: [1, 1.3, 1] }} transition={{ duration: 0.8, repeat: Infinity }} className="w-1.5 h-1.5 rounded-full bg-[#818cf8]" />}
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ActiveLivenessPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string>();
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [verifying, setVerifying] = useState(false);
  const [result, setResult] = useState<VerifyResult | null>(null);
  const [timeLeft, setTimeLeft] = useState(60);
  const [generating, setGenerating] = useState(false);
  const [autoVerify, setAutoVerify] = useState(false);
  const [lastVerifyMs, setLastVerifyMs] = useState<number | null>(null);

  // ── Camera ───────────────────────────────────────────────────────────────
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
      setCameraError("Camera access required for liveness challenges.");
    }
  }, []);

  useEffect(() => {
    startCamera();
    return () => {
      streamRef.current?.getTracks().forEach(t => t.stop());
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [startCamera]);

  // ── Timer ────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!challenge || result) return;
    setTimeLeft(challenge.expires_in_seconds);
    const timer = setInterval(() => {
      setTimeLeft(t => {
        if (t <= 1) {
          clearInterval(timer);
          setChallenge(null);
          toast.error("Challenge expired. Generate a new one.");
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [challenge, result]);

  // ── Capture frame ────────────────────────────────────────────────────────
  const captureFrame = useCallback((): Promise<Blob | null> => {
    return new Promise(resolve => {
      if (!videoRef.current || !canvasRef.current) return resolve(null);
      const v = videoRef.current, c = canvasRef.current;
      c.width = v.videoWidth; c.height = v.videoHeight;
      c.getContext("2d")?.drawImage(v, 0, 0);
      c.toBlob(blob => resolve(blob), "image/jpeg", 0.90);
    });
  }, []);

  // ── Generate challenge ───────────────────────────────────────────────────
  const generateChallenge = async () => {
    setGenerating(true);
    setResult(null);
    setCompletedSteps([]);
    setAutoVerify(false);
    if (pollingRef.current) clearInterval(pollingRef.current);

    try {
      const lastType = challenge?.challenge_type;
      const fd = new FormData();
      if (lastType) fd.append("last_challenge_type", lastType);

      const { data } = await livenessApi.generateChallenge(undefined, lastType);
      setChallenge(data);
      toast.success(`Challenge: ${data.challenge_type.replace(/_/g, " ")}`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to generate challenge");
    } finally {
      setGenerating(false);
    }
  };

  // ── Verify one frame ─────────────────────────────────────────────────────
  const verifyFrame = useCallback(async () => {
    if (!challenge || verifying || result?.challenge_completed) return;
    setVerifying(true);
    const t0 = performance.now();

    try {
      const blob = await captureFrame();
      if (!blob) return;

      const fd = new FormData();
      fd.append("challenge_id", challenge.challenge_id);
      fd.append("nonce", challenge.nonce);
      fd.append("completed_steps", JSON.stringify(completedSteps));
      fd.append("image", blob, "frame.jpg");

      const { data } = await livenessApi.verifyChallenge(fd);
      const elapsed = Math.round(performance.now() - t0);
      setLastVerifyMs(elapsed);

      if (data.steps_completed.length > completedSteps.length) {
        const newStep = data.steps_completed[data.steps_completed.length - 1];
        toast.success(`✓ ${newStep.replace("_", " ")} detected!`);
        setCompletedSteps(data.steps_completed);
      }

      if (data.challenge_completed) {
        setResult(data);
        setAutoVerify(false);
        if (pollingRef.current) clearInterval(pollingRef.current);
        toast.success("Challenge completed! 🎉");
      }
    } catch (e: any) {
      if (e?.response?.status !== 404) {
        console.warn("Verify frame error:", e?.response?.data?.detail);
      }
    } finally {
      setVerifying(false);
    }
  }, [challenge, verifying, result, completedSteps, captureFrame]);

  // ── Auto-verify polling (every 800ms when enabled) ───────────────────────
  useEffect(() => {
    if (autoVerify && challenge && !result) {
      pollingRef.current = setInterval(verifyFrame, 900);
    } else {
      if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [autoVerify, challenge, result, verifyFrame]);

  const pendingSteps = challenge ? challenge.steps.slice(completedSteps.length) : [];
  const currentAction = pendingSteps[0];
  const progressPct = challenge ? (completedSteps.length / challenge.steps.length) * 100 : 0;

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-bold text-white tracking-tight">Active Liveness Challenge</h1>
        <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
          Randomized human interaction challenges using MediaPipe 468-landmark face mesh
        </p>
      </div>

      <div className="grid lg:grid-cols-[1fr,340px] gap-5">
        {/* Camera */}
        <div className="space-y-4">
          <div className="rounded-2xl overflow-hidden"
            style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="relative bg-black" style={{ aspectRatio: "4/3" }}>
              {cameraError ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6">
                  <Eye size={32} style={{ color: "rgba(255,255,255,0.15)" }} />
                  <p className="text-sm text-center text-[rgba(255,255,255,0.3)]">{cameraError}</p>
                  <button onClick={startCamera} className="px-4 py-2 rounded-xl text-sm font-medium"
                    style={{ background: "rgba(0,194,255,0.15)", border: "1px solid rgba(0,194,255,0.3)", color: "#00C2FF" }}>
                    Enable Camera
                  </button>
                </div>
              ) : (
                <>
                  <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />

                  {/* Face guide oval */}
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                    <div className="relative w-48 h-60">
                      <motion.div
                        animate={{
                          borderColor: autoVerify
                            ? ["rgba(0,194,255,0.9)", "rgba(0,229,168,0.9)", "rgba(0,194,255,0.9)"]
                            : challenge && !result
                            ? "rgba(0,194,255,0.6)"
                            : result?.challenge_completed
                            ? "rgba(0,229,168,0.8)"
                            : "rgba(255,255,255,0.2)"
                        }}
                        transition={{ duration: 1.2, repeat: autoVerify ? Infinity : 0 }}
                        className="absolute inset-0 rounded-full border-2"
                      />
                      {/* Corner brackets */}
                      {["top-0 left-0 border-t-2 border-l-2", "top-0 right-0 border-t-2 border-r-2",
                        "bottom-0 left-0 border-b-2 border-l-2", "bottom-0 right-0 border-b-2 border-r-2"].map((cls, i) => (
                        <div key={i} className={`absolute w-4 h-4 ${cls} border-[#00C2FF] opacity-80`} />
                      ))}
                    </div>
                  </div>

                  {/* Current action prompt */}
                  {challenge && !result && currentAction && (
                    <motion.div
                      key={currentAction}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="absolute bottom-4 inset-x-4 flex items-center justify-center"
                    >
                      <div className="flex items-center gap-2.5 px-4 py-3 rounded-2xl text-sm font-semibold"
                        style={{ background: "rgba(0,0,0,0.85)", border: "1px solid rgba(0,194,255,0.3)", color: "white", backdropFilter: "blur(12px)" }}>
                        <span className="text-xl">{ACTION_ICONS[currentAction] ?? "🎯"}</span>
                        <span>{challenge.descriptions[challenge.steps.indexOf(currentAction)]}</span>
                        {verifying && <Loader2 size={14} className="animate-spin text-[#00C2FF] ml-1" />}
                      </div>
                    </motion.div>
                  )}

                  {/* Timer */}
                  {challenge && !result && (
                    <div className="absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px]"
                      style={{
                        background: "rgba(0,0,0,0.7)",
                        color: timeLeft < 15 ? "#f87171" : "rgba(255,255,255,0.5)",
                        border: timeLeft < 15 ? "1px solid rgba(248,113,113,0.3)" : "none",
                      }}>
                      <Clock size={9} />
                      {timeLeft}s
                    </div>
                  )}

                  {/* Auto-verify status */}
                  {autoVerify && !result && (
                    <div className="absolute top-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px]"
                      style={{ background: "rgba(0,0,0,0.7)", color: "#00C2FF" }}>
                      <span className="w-1.5 h-1.5 rounded-full bg-[#00C2FF] animate-pulse" />
                      DETECTING
                    </div>
                  )}

                  {/* Success overlay */}
                  <AnimatePresence>
                    {result?.challenge_completed && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="absolute inset-0 flex flex-col items-center justify-center gap-4"
                        style={{ background: "rgba(0,229,168,0.08)", backdropFilter: "blur(4px)" }}
                      >
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: "spring", stiffness: 200, damping: 14 }}
                          className="w-20 h-20 rounded-full flex items-center justify-center"
                          style={{ background: "rgba(0,229,168,0.2)", border: "2px solid rgba(0,229,168,0.5)" }}
                        >
                          <CheckCircle2 size={36} style={{ color: "#00E5A8" }} />
                        </motion.div>
                        <p className="text-lg font-bold text-white">Liveness Verified!</p>
                        <p className="text-[12px] text-[rgba(255,255,255,0.5)]">{result.confidence.toFixed(0)}% confidence</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </>
              )}
              <canvas ref={canvasRef} className="hidden" />
            </div>

            {/* Progress bar */}
            {challenge && (
              <div className="px-4 pt-3 pb-1">
                <div className="flex items-center justify-between text-[10px] text-[rgba(255,255,255,0.3)] mb-1.5">
                  <span>Progress</span>
                  <span>{completedSteps.length}/{challenge.steps.length} steps</span>
                </div>
                <div className="h-1.5 rounded-full bg-[rgba(255,255,255,0.06)]">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: "linear-gradient(90deg, #00C2FF, #00E5A8)" }}
                    animate={{ width: `${progressPct}%` }}
                    transition={{ duration: 0.4 }}
                  />
                </div>
              </div>
            )}

            {/* Controls */}
            <div className="p-4 space-y-3">
              {!challenge || result ? (
                <button
                  onClick={generateChallenge}
                  disabled={generating || !cameraReady}
                  className="w-full py-3.5 rounded-xl text-[13.5px] font-bold flex items-center justify-center gap-2.5 transition-all"
                  style={{
                    background: "linear-gradient(135deg, rgba(0,194,255,0.2), rgba(0,229,168,0.15))",
                    border: "1px solid rgba(0,194,255,0.35)",
                    color: "white",
                    cursor: generating || !cameraReady ? "not-allowed" : "pointer",
                    opacity: generating || !cameraReady ? 0.5 : 1,
                  }}
                >
                  {generating
                    ? <><Loader2 size={16} className="animate-spin" /> Generating…</>
                    : <><Target size={16} /> {result ? "New Challenge" : "Generate Challenge"}</>
                  }
                </button>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={verifyFrame}
                    disabled={verifying || !cameraReady}
                    className="py-3 rounded-xl text-[12.5px] font-semibold flex items-center justify-center gap-2 transition-all"
                    style={{
                      background: "rgba(0,194,255,0.12)",
                      border: "1px solid rgba(0,194,255,0.3)",
                      color: "#00C2FF",
                      cursor: verifying || !cameraReady ? "not-allowed" : "pointer",
                      opacity: verifying ? 0.6 : 1,
                    }}
                  >
                    {verifying ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />}
                    {verifying ? "Checking…" : "Check Frame"}
                  </button>
                  <button
                    onClick={() => setAutoVerify(a => !a)}
                    className="py-3 rounded-xl text-[12.5px] font-semibold flex items-center justify-center gap-2 transition-all"
                    style={{
                      background: autoVerify ? "rgba(0,229,168,0.12)" : "rgba(255,255,255,0.04)",
                      border: `1px solid ${autoVerify ? "rgba(0,229,168,0.35)" : "rgba(255,255,255,0.1)"}`,
                      color: autoVerify ? "#00E5A8" : "rgba(255,255,255,0.4)",
                    }}
                  >
                    <Zap size={13} />
                    {autoVerify ? "Auto ON" : "Auto OFF"}
                  </button>
                </div>
              )}
              {challenge && !result && (
                <button
                  onClick={generateChallenge}
                  className="w-full py-2 rounded-xl text-[11px] font-medium transition-all"
                  style={{ color: "rgba(255,255,255,0.25)", background: "none", border: "1px solid rgba(255,255,255,0.06)" }}
                >
                  <RefreshCw size={10} className="inline mr-1.5" />
                  New Challenge
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Challenge info */}
          {challenge ? (
            <div className="rounded-2xl p-4 space-y-4"
              style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] text-[rgba(255,255,255,0.3)] mb-0.5">Challenge Type</p>
                  <p className="text-sm font-bold text-white capitalize">{challenge.challenge_type.replace(/_/g, " ")}</p>
                </div>
                <div className="px-2 py-0.5 rounded-full text-[9.5px] font-semibold capitalize"
                  style={{
                    background: `${DIFFICULTY_COLOR[challenge.difficulty] ?? "#9ca3af"}15`,
                    border: `1px solid ${DIFFICULTY_COLOR[challenge.difficulty] ?? "#9ca3af"}30`,
                    color: DIFFICULTY_COLOR[challenge.difficulty] ?? "#9ca3af",
                  }}>
                  {challenge.difficulty}
                </div>
              </div>

              <div>
                <p className="text-[10px] text-[rgba(255,255,255,0.25)] mb-2 uppercase tracking-wider font-semibold">Steps Required</p>
                <div className="flex flex-wrap gap-2">
                  {challenge.steps.map((step, idx) => (
                    <StepPill
                      key={idx}
                      action={step}
                      status={
                        idx < completedSteps.length ? "done"
                        : idx === completedSteps.length ? "active"
                        : "pending"
                      }
                    />
                  ))}
                </div>
              </div>

              {/* Instructions */}
              <div className="space-y-1.5">
                <p className="text-[10px] text-[rgba(255,255,255,0.25)] uppercase tracking-wider font-semibold">Instructions</p>
                {challenge.descriptions.map((desc, i) => (
                  <div key={i} className="flex items-center gap-2 text-[12px]"
                    style={{ color: completedSteps.length > i ? "#00E5A8" : i === completedSteps.length ? "white" : "rgba(255,255,255,0.35)" }}>
                    <span>{i + 1}.</span>
                    {completedSteps.length > i
                      ? <><CheckCircle2 size={11} /><span className="line-through opacity-60">{desc}</span></>
                      : <span>{desc}</span>
                    }
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl p-6 flex flex-col items-center justify-center gap-3 text-center"
              style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.08)", minHeight: 160 }}>
              <Eye size={28} style={{ color: "rgba(255,255,255,0.1)" }} />
              <p className="text-[12px] text-[rgba(255,255,255,0.25)]">
                Generate a challenge to start liveness verification
              </p>
            </div>
          )}

          {/* Result */}
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl p-4 space-y-3"
                style={{
                  background: result.challenge_completed ? "rgba(0,229,168,0.06)" : "rgba(248,113,113,0.06)",
                  border: `1px solid ${result.challenge_completed ? "rgba(0,229,168,0.2)" : "rgba(248,113,113,0.2)"}`,
                }}
              >
                <div className="flex items-center gap-2">
                  {result.challenge_completed
                    ? <CheckCircle2 size={16} style={{ color: "#00E5A8" }} />
                    : <XCircle size={16} style={{ color: "#f87171" }} />
                  }
                  <span className="text-sm font-bold" style={{ color: result.challenge_completed ? "#00E5A8" : "#f87171" }}>
                    {result.challenge_completed ? "Challenge Passed" : "Challenge Failed"}
                  </span>
                </div>
                <div className="space-y-1.5 text-[11.5px]">
                  {[
                    { l: "Confidence", v: `${result.confidence.toFixed(0)}%` },
                    { l: "Steps Completed", v: `${result.steps_completed.length}/${(result.steps_completed.length + result.steps_pending.length)}` },
                    { l: "Inference Time", v: lastVerifyMs ? `${lastVerifyMs}ms` : "—" },
                    ...(result.failure_reason ? [{ l: "Reason", v: result.failure_reason }] : []),
                  ].map(({ l, v }) => (
                    <div key={l} className="flex justify-between">
                      <span className="text-[rgba(255,255,255,0.35)]">{l}</span>
                      <span className="font-medium text-white">{v}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* How it works */}
          <div className="rounded-2xl p-4 space-y-2.5"
            style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.35)] uppercase tracking-wider">How It Works</p>
            {[
              { step: "1", text: "Server generates a unique randomized challenge (never repeats consecutively)" },
              { step: "2", text: "You perform the facial action — camera streams to MediaPipe 468-landmark mesh" },
              { step: "3", text: "EAR blink detection, yaw/pitch estimation, mouth ratio verify each action" },
              { step: "4", text: "Challenge nonce prevents replay attacks · 60s TTL enforced" },
            ].map(({ step, text }) => (
              <div key={step} className="flex gap-2.5 text-[10.5px]">
                <span className="w-4 h-4 rounded-full flex items-center justify-center shrink-0 text-[9px] font-bold"
                  style={{ background: "rgba(0,194,255,0.12)", border: "1px solid rgba(0,194,255,0.2)", color: "#00C2FF" }}>
                  {step}
                </span>
                <span className="text-[rgba(255,255,255,0.3)] leading-relaxed">{text}</span>
              </div>
            ))}
          </div>

          {/* Challenge catalog preview */}
          <div className="rounded-2xl p-4"
            style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.35)] uppercase tracking-wider mb-3">Available Challenges</p>
            <div className="flex flex-wrap gap-1.5">
              {[
                "blink_twice", "turn_left_smile", "open_mouth_blink",
                "look_up_smile", "raise_eyebrows_turn_right",
                "smile_blink", "turn_right_open_mouth", "look_down_blink",
              ].map(type => (
                <span key={type} className="px-2 py-0.5 rounded text-[9.5px]"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.3)" }}>
                  {type.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
