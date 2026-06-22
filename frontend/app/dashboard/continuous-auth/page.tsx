"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck, ShieldAlert, ShieldOff, Eye, Activity,
  Play, Square, RefreshCw, Clock, AlertTriangle, CheckCircle2,
  Loader2, Zap, TrendingDown,
} from "lucide-react";
import { toast } from "sonner";
import { continuousAuthApi, deviceTrustApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ContinuousSession, ContinuousCheckResult } from "@/types";

// ── Trust timeline item ───────────────────────────────────────────────────────
interface TimelineEvent {
  time: string;
  score: number;
  action: string;
  check_score: number;
}

function TimelineItem({ event, index }: { event: TimelineEvent; index: number }) {
  const color = event.score >= 90 ? "#00E5A8" : event.score >= 70 ? "#f59e0b" : "#f87171";
  const actionColors: Record<string, string> = {
    continue: "#00E5A8",
    reauth_required: "#f59e0b",
    suspend: "#f87171",
    terminate: "#f87171",
  };
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
      className="flex items-center gap-3 text-[11px] py-1.5"
    >
      <span className="text-[rgba(255,255,255,0.2)] w-16 shrink-0 font-mono text-[10px]">{event.time}</span>
      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color, boxShadow: `0 0 4px ${color}` }} />
      <div className="flex-1 flex items-center justify-between">
        <span style={{ color: actionColors[event.action] ?? "rgba(255,255,255,0.5)" }}>
          {event.action.replace("_", " ")}
        </span>
        <span className="font-bold" style={{ color }}>{event.score.toFixed(0)}</span>
      </div>
    </motion.div>
  );
}

// ── Score arc ─────────────────────────────────────────────────────────────────
function ScoreArc({ score, status }: { score: number; status: string }) {
  const color = status === "active" ? (score >= 90 ? "#00E5A8" : score >= 70 ? "#f59e0b" : "#f87171")
    : status === "terminated" ? "#f87171" : "#9ca3af";
  const r = 52;
  const circ = 2 * Math.PI * r;
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: 128, height: 128 }}>
        <svg width={128} height={128} className="-rotate-90">
          <circle cx={64} cy={64} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={9} />
          <motion.circle
            cx={64} cy={64} r={r} fill="none" stroke={color} strokeWidth={9}
            strokeLinecap="round" strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - (score / 100) * circ }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold" style={{ color }}>{score.toFixed(0)}</span>
          <span className="text-[9px] text-[rgba(255,255,255,0.25)] mt-0.5">trust score</span>
        </div>
      </div>
      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-semibold capitalize"
        style={{
          background: `${color}12`,
          border: `1px solid ${color}25`,
          color,
        }}>
        {status === "active" && <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: color }} />}
        {status.replace("_", " ")}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ContinuousAuthPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const checkIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [cameraReady, setCameraReady] = useState(false);
  const [session, setSession] = useState<ContinuousSession | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [checking, setChecking] = useState(false);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [checkInterval, setCheckInterval] = useState(30);
  const [nextCheckIn, setNextCheckIn] = useState<number | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Camera
  const startCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => { videoRef.current?.play(); setCameraReady(true); };
      }
    } catch {
      toast.error("Camera access needed for continuous auth");
    }
  }, []);

  useEffect(() => {
    startCamera();
    return () => {
      streamRef.current?.getTracks().forEach(t => t.stop());
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [startCamera]);

  // Start session
  const startSession = async () => {
    setStarting(true);
    try {
      const fd = new FormData();
      fd.append("check_interval", String(checkInterval));
      const { data } = await continuousAuthApi.startSession(checkInterval);
      setSession(data);
      setSessionToken(data.session_token);
      setTimeline([]);
      toast.success("Continuous auth session started");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to start session");
    } finally {
      setStarting(false);
    }
  };

  // Perform a check
  const performCheck = useCallback(async () => {
    if (!sessionToken || checking) return;
    setChecking(true);
    try {
      const fd = new FormData();
      fd.append("session_token", sessionToken);

      // Capture frame if camera ready
      if (videoRef.current && canvasRef.current && cameraReady) {
        const v = videoRef.current, c = canvasRef.current;
        c.width = v.videoWidth; c.height = v.videoHeight;
        c.getContext("2d")?.drawImage(v, 0, 0);
        await new Promise<void>(resolve => {
          c.toBlob(blob => {
            if (blob) fd.append("image", blob, "frame.jpg");
            resolve();
          }, "image/jpeg", 0.85);
        });
      }

      // Device signals
      try {
        const cameras = await navigator.mediaDevices.enumerateDevices()
          .then(devs => devs.filter(d => d.kind === "videoinput").map(d => ({ label: d.label, deviceId: d.deviceId })));
        const deviceResult = await deviceTrustApi.assess({
          platform: "web",
          navigator_webdriver: !!(navigator as any).webdriver,
          camera_ids: cameras,
        });
        fd.append("device_signals", JSON.stringify({ platform: "web", navigator_webdriver: !!(navigator as any).webdriver }));
      } catch { /* non-fatal */ }

      const { data } = await continuousAuthApi.check(fd) as { data: ContinuousCheckResult };
      setNextCheckIn(data.next_check_in_seconds);

      // Update session state
      setSession(s => s ? { ...s, status: data.status as any, current_trust_score: data.trust_score } : s);

      // Add to timeline
      setTimeline(t => [{
        time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }),
        score: data.trust_score,
        action: data.action,
        check_score: data.check_score,
      }, ...t].slice(0, 20));

      if (data.action === "reauth_required") {
        toast.warning("Trust score dropped — re-authentication required");
      } else if (data.action === "suspend") {
        toast.error("Session suspended");
        if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
      } else if (data.action === "terminate") {
        toast.error("Session terminated");
        if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
        setSessionToken(null);
      }
    } catch (e: any) {
      if (e?.response?.status === 410) {
        toast.error("Session terminated");
        setSessionToken(null);
        if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
      }
    } finally {
      setChecking(false);
    }
  }, [sessionToken, checking, cameraReady]);

  // Auto-check interval
  useEffect(() => {
    if (!sessionToken || !session || session.status === "terminated") return;

    // Countdown
    if (countdownRef.current) clearInterval(countdownRef.current);
    setNextCheckIn(checkInterval);
    countdownRef.current = setInterval(() => {
      setNextCheckIn(n => n !== null ? Math.max(0, n - 1) : null);
    }, 1000);

    // Actual check interval
    if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
    checkIntervalRef.current = setInterval(performCheck, checkInterval * 1000);

    return () => {
      if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [sessionToken, session?.status, checkInterval, performCheck]);

  // End session
  const endSession = async () => {
    if (!sessionToken) return;
    try {
      const fd = new FormData();
      fd.append("session_token", sessionToken);
      fd.append("reason", "user_logout");
      await continuousAuthApi.endSession(sessionToken);
      toast.success("Session ended");
    } catch { /* ignore */ }
    setSessionToken(null);
    setSession(null);
    if (checkIntervalRef.current) clearInterval(checkIntervalRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
  };

  const isActive = session?.status === "active";
  const currentScore = session?.current_trust_score ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-[22px] font-bold text-white tracking-tight">Continuous Authentication</h1>
        <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
          Periodic biometric checks every {checkInterval}s — face presence + eye tracking + device trust
        </p>
      </div>

      <div className="grid lg:grid-cols-[1fr,360px] gap-5">
        {/* Left — camera + controls */}
        <div className="space-y-4">
          {/* Camera */}
          <div className="rounded-2xl overflow-hidden"
            style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="relative bg-black" style={{ aspectRatio: "4/3" }}>
              <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />

              {/* Status overlay */}
              {session && (
                <div className="absolute inset-0 pointer-events-none">
                  {/* Face guide */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="relative w-44 h-56">
                      <motion.div
                        animate={{ borderColor: checking ? ["rgba(0,194,255,0.9)", "rgba(0,229,168,0.9)", "rgba(0,194,255,0.9)"] : isActive ? "rgba(0,194,255,0.5)" : "rgba(248,113,113,0.5)" }}
                        transition={{ duration: 1, repeat: checking ? Infinity : 0 }}
                        className="absolute inset-0 rounded-full border-2"
                      />
                    </div>
                  </div>

                  {/* Score badge */}
                  <div className="absolute top-3 left-3">
                    <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[11px] font-bold"
                      style={{
                        background: "rgba(0,0,0,0.8)",
                        color: currentScore >= 90 ? "#00E5A8" : currentScore >= 70 ? "#f59e0b" : "#f87171",
                      }}>
                      <ShieldCheck size={11} />
                      Trust: {currentScore.toFixed(0)}
                    </div>
                  </div>

                  {/* Status */}
                  <div className="absolute top-3 right-3">
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[9.5px]"
                      style={{
                        background: "rgba(0,0,0,0.8)",
                        color: isActive ? "#00E5A8" : "#f87171",
                      }}>
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: isActive ? "#00E5A8" : "#f87171", animation: isActive ? "pulse 1.5s infinite" : "none" }} />
                      {session.status.replace("_", " ").toUpperCase()}
                    </div>
                  </div>

                  {/* Check countdown */}
                  {nextCheckIn !== null && isActive && (
                    <div className="absolute bottom-3 right-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px]"
                      style={{ background: "rgba(0,0,0,0.7)", color: "rgba(255,255,255,0.4)" }}>
                      <Clock size={9} />
                      Next check: {nextCheckIn}s
                    </div>
                  )}

                  {checking && (
                    <div className="absolute bottom-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px]"
                      style={{ background: "rgba(0,0,0,0.7)", color: "#00C2FF" }}>
                      <Loader2 size={9} className="animate-spin" />
                      Checking…
                    </div>
                  )}
                </div>
              )}
              <canvas ref={canvasRef} className="hidden" />
            </div>

            <div className="p-4 space-y-3">
              {/* Interval selector */}
              {!session && (
                <div>
                  <div className="flex justify-between text-[10px] text-[rgba(255,255,255,0.35)] mb-1.5">
                    <span>Check interval</span>
                    <span className="font-medium text-white">{checkInterval}s</span>
                  </div>
                  <input type="range" min={10} max={120} step={10} value={checkInterval}
                    onChange={e => setCheckInterval(Number(e.target.value))}
                    className="w-full" style={{ accentColor: "#00C2FF" }} />
                  <div className="flex justify-between text-[9px] text-[rgba(255,255,255,0.2)] mt-0.5">
                    <span>10s (aggressive)</span>
                    <span>120s (relaxed)</span>
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                {!session ? (
                  <button onClick={startSession} disabled={starting || !cameraReady}
                    className="flex-1 py-3.5 rounded-xl text-[13px] font-bold flex items-center justify-center gap-2 transition-all"
                    style={{
                      background: "linear-gradient(135deg, rgba(0,194,255,0.2), rgba(0,229,168,0.15))",
                      border: "1px solid rgba(0,194,255,0.35)",
                      color: "white",
                      cursor: starting || !cameraReady ? "not-allowed" : "pointer",
                      opacity: starting || !cameraReady ? 0.5 : 1,
                    }}>
                    {starting ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
                    {starting ? "Starting…" : "Start Session"}
                  </button>
                ) : (
                  <>
                    <button onClick={performCheck} disabled={checking || session?.status === "terminated"}
                      className="flex-1 py-3 rounded-xl text-[12px] font-semibold flex items-center justify-center gap-2 transition-all"
                      style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF", opacity: checking ? 0.6 : 1 }}>
                      {checking ? <Loader2 size={13} className="animate-spin" /> : <Eye size={13} />}
                      Check Now
                    </button>
                    <button onClick={endSession}
                      className="flex-1 py-3 rounded-xl text-[12px] font-semibold flex items-center justify-center gap-2 transition-all"
                      style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)", color: "#f87171" }}>
                      <Square size={13} />
                      End Session
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Timeline */}
          {timeline.length > 0 && (
            <div className="rounded-2xl p-4"
              style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div className="flex items-center justify-between mb-3">
                <p className="text-[12px] font-semibold text-white">Check Timeline</p>
                <p className="text-[10px] text-[rgba(255,255,255,0.25)]">{timeline.length} checks</p>
              </div>
              <div className="space-y-0.5 max-h-48 overflow-y-auto">
                {timeline.map((ev, i) => <TimelineItem key={i} event={ev} index={i} />)}
              </div>
            </div>
          )}
        </div>

        {/* Right — session info + score arc */}
        <div className="space-y-4">
          {/* Session status */}
          <div className="rounded-2xl p-5 flex flex-col items-center gap-4"
            style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
            {session ? (
              <>
                <ScoreArc score={currentScore} status={session.status} />
                <div className="w-full space-y-1.5 text-[11.5px]">
                  {[
                    { l: "Status", v: session.status.replace("_", " "), color: isActive ? "#00E5A8" : "#f87171" },
                    { l: "Check Interval", v: `${session.check_interval_seconds}s` },
                    { l: "Re-auth Count", v: String(session.reauth_count) },
                    { l: "Session Start", v: new Date(session.started_at).toLocaleTimeString() },
                    { l: "Last Verified", v: session.last_verified_at ? new Date(session.last_verified_at).toLocaleTimeString() : "—" },
                  ].map(({ l, v, color }) => (
                    <div key={l} className="flex justify-between">
                      <span className="text-[rgba(255,255,255,0.35)]">{l}</span>
                      <span className="font-medium" style={{ color: color ?? "rgba(255,255,255,0.75)" }}>{v}</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center py-6 gap-3">
                <div className="w-16 h-16 rounded-full flex items-center justify-center"
                  style={{ background: "rgba(0,194,255,0.06)", border: "1px solid rgba(0,194,255,0.12)" }}>
                  <ShieldCheck size={24} style={{ color: "rgba(0,194,255,0.3)" }} />
                </div>
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] text-center">
                  Start a session to begin continuous biometric monitoring
                </p>
              </div>
            )}
          </div>

          {/* Score threshold legend */}
          <div className="rounded-2xl p-4 space-y-2.5"
            style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.35)] uppercase tracking-wider">Score Thresholds</p>
            {[
              { range: "≥ 90", label: "Continue session", icon: CheckCircle2, color: "#00E5A8" },
              { range: "70–89", label: "Request re-auth", icon: AlertTriangle, color: "#f59e0b" },
              { range: "50–69", label: "Suspend session", icon: ShieldAlert, color: "#f87171" },
              { range: "< 50", label: "Terminate immediately", icon: ShieldOff, color: "#f87171" },
            ].map(({ range, label, icon: Icon, color }) => (
              <div key={range} className="flex items-center gap-2.5 text-[11px]">
                <Icon size={12} style={{ color }} />
                <span className="font-mono" style={{ color }}>{range}</span>
                <span className="text-[rgba(255,255,255,0.35)]">{label}</span>
              </div>
            ))}
          </div>

          {/* What is checked */}
          <div className="rounded-2xl p-4 space-y-2.5"
            style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.35)] uppercase tracking-wider">Every Check Performs</p>
            {[
              { icon: Eye,          label: "Face Presence",    weight: "40%", color: "#00E5A8" },
              { icon: Activity,     label: "Eye Tracking",     weight: "20%", color: "#00C2FF" },
              { icon: ShieldCheck,  label: "Device Trust",     weight: "25%", color: "#818cf8" },
              { icon: Zap,          label: "Behavioral Score", weight: "15%", color: "#f59e0b" },
            ].map(({ icon: Icon, label, weight, color }) => (
              <div key={label} className="flex items-center gap-2.5 text-[11px]">
                <Icon size={12} style={{ color }} />
                <span className="flex-1 text-[rgba(255,255,255,0.5)]">{label}</span>
                <span className="font-mono font-semibold" style={{ color }}>{weight}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
