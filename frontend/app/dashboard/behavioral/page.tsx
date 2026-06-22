"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Zap, Mouse, Keyboard, Smartphone, Activity, CheckCircle2,
  AlertTriangle, TrendingUp, BarChart3, Info, RefreshCw, Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { behavioralApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { BehaviorScoreResult, BehaviorProfileResult } from "@/types";

// ── Mini score bar ────────────────────────────────────────────────────────────
function ScoreBar({ score, color }: { score: number; color: string }) {
  return (
    <div className="h-1.5 rounded-full bg-[rgba(255,255,255,0.06)] overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(100, score)}%` }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}

// ── Score gauge ────────────────────────────────────────────────────────────────
function BehaviorGauge({ score }: { score: number }) {
  const color = score >= 80 ? "#00E5A8" : score >= 60 ? "#f59e0b" : "#f87171";
  const r = 44;
  const circ = 2 * Math.PI * r;
  const arc = (score / 100) * circ * 0.75; // 270° arc
  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: 120, height: 120 }}>
        <svg width={120} height={120} style={{ transform: "rotate(135deg)" }}>
          <circle cx={60} cy={60} r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth={8}
            strokeDasharray={`${circ * 0.75} ${circ}`} strokeLinecap="round" />
          <motion.circle
            cx={60} cy={60} r={r} fill="none" stroke={color} strokeWidth={8}
            strokeLinecap="round"
            strokeDasharray={`${circ * 0.75} ${circ}`}
            initial={{ strokeDashoffset: circ * 0.75 }}
            animate={{ strokeDashoffset: circ * 0.75 - arc }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold" style={{ color }}>{score.toFixed(0)}</span>
          <span className="text-[9px] text-[rgba(255,255,255,0.3)]">/ 100</span>
        </div>
      </div>
      <div className="text-[11px] font-semibold mt-1" style={{ color }}>
        {score >= 80 ? "Trusted" : score >= 60 ? "Review" : "Anomalous"}
      </div>
    </div>
  );
}

// ── Modality card ─────────────────────────────────────────────────────────────
function ModalityCard({
  icon: Icon, label, color, score, fields, onSubmit, submitting,
}: {
  icon: any; label: string; color: string; score: number | null;
  fields: Array<{ key: string; label: string; unit: string; min: number; max: number; step: number; default: number }>;
  onSubmit: (metrics: Record<string, number>) => void;
  submitting: boolean;
}) {
  const [values, setValues] = useState<Record<string, number>>(
    Object.fromEntries(fields.map(f => [f.key, f.default]))
  );

  return (
    <div className="rounded-2xl p-4 space-y-3"
      style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: `${color}15`, border: `1px solid ${color}25` }}>
            <Icon size={13} style={{ color }} />
          </div>
          <span className="text-[12.5px] font-semibold text-white">{label}</span>
        </div>
        {score !== null && (
          <div className="text-[11px] font-bold px-2 py-0.5 rounded"
            style={{ background: `${score >= 80 ? "#00E5A8" : score >= 60 ? "#f59e0b" : "#f87171"}15`, color: score >= 80 ? "#00E5A8" : score >= 60 ? "#f59e0b" : "#f87171" }}>
            {score.toFixed(0)}
          </div>
        )}
      </div>

      <div className="space-y-3">
        {fields.map(f => (
          <div key={f.key}>
            <div className="flex justify-between text-[10px] text-[rgba(255,255,255,0.35)] mb-1">
              <span>{f.label}</span>
              <span className="font-medium text-white">{values[f.key]}{f.unit}</span>
            </div>
            <input
              type="range" min={f.min} max={f.max} step={f.step} value={values[f.key]}
              onChange={e => setValues(v => ({ ...v, [f.key]: Number(e.target.value) }))}
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
              style={{ accentColor: color }}
            />
          </div>
        ))}
      </div>

      <button
        onClick={() => onSubmit(values)}
        disabled={submitting}
        className="w-full py-2.5 rounded-xl text-[12px] font-semibold flex items-center justify-center gap-2 transition-all"
        style={{
          background: `${color}12`,
          border: `1px solid ${color}25`,
          color,
          cursor: submitting ? "not-allowed" : "pointer",
          opacity: submitting ? 0.6 : 1,
        }}
      >
        {submitting ? <Loader2 size={12} className="animate-spin" /> : <Activity size={12} />}
        {submitting ? "Submitting…" : "Submit Event"}
      </button>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function BehavioralPage() {
  const [behaviorScore, setBehaviorScore] = useState<BehaviorScoreResult | null>(null);
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});
  const [totalSubmitted, setTotalSubmitted] = useState(0);

  // Mouse tracking state
  const mousePosRef = useRef({ x: 0, y: 0, t: Date.now() });
  const [mouseMetrics, setMouseMetrics] = useState({ speed: 0, curvature: 0, hesitation: 0 });
  const mouseHistory = useRef<Array<{ x: number; y: number; t: number }>>([]);

  // Keyboard tracking
  const [keyMetrics, setKeyMetrics] = useState({ wpm: 0, dwell: 0, flight: 0 });
  const keyTimes = useRef<Record<string, number>>({});
  const keyDownTimes = useRef<Array<{ key: string; down: number; up: number }>>([]);
  const typingStartRef = useRef<number | null>(null);
  const wordCountRef = useRef(0);

  // ── Auto mouse tracking ───────────────────────────────────────────────────
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const now = Date.now();
      const prev = mousePosRef.current;
      const dt = (now - prev.t) / 1000;
      if (dt < 0.01) return;

      const dx = e.clientX - prev.x;
      const dy = e.clientY - prev.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const speed = dist / dt;

      mouseHistory.current.push({ x: e.clientX, y: e.clientY, t: now });
      if (mouseHistory.current.length > 20) mouseHistory.current.shift();

      // Curvature: variance in angle changes
      let curvature = 0;
      if (mouseHistory.current.length >= 3) {
        const pts = mouseHistory.current.slice(-10);
        const angles: number[] = [];
        for (let i = 1; i < pts.length - 1; i++) {
          const a1 = Math.atan2(pts[i].y - pts[i - 1].y, pts[i].x - pts[i - 1].x);
          const a2 = Math.atan2(pts[i + 1].y - pts[i].y, pts[i + 1].x - pts[i].x);
          angles.push(Math.abs(a2 - a1));
        }
        curvature = angles.reduce((s, a) => s + a, 0) / angles.length;
      }

      mousePosRef.current = { x: e.clientX, y: e.clientY, t: now };
      setMouseMetrics(m => ({
        speed: Math.round(speed * 0.3 + m.speed * 0.7),
        curvature: Math.round(curvature * 100) / 100,
        hesitation: speed < 20 ? Math.min(1, m.hesitation + 0.05) : Math.max(0, m.hesitation - 0.02),
      }));
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // ── Auto keyboard tracking ────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key.length !== 1 && e.key !== "Backspace") return;
      keyTimes.current[e.key] = Date.now();
      if (typingStartRef.current === null) typingStartRef.current = Date.now();
      if (e.key === " ") wordCountRef.current++;
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (!keyTimes.current[e.key]) return;
      const down = keyTimes.current[e.key];
      const up = Date.now();
      const dwell = up - down;

      keyDownTimes.current.push({ key: e.key, down, up });
      if (keyDownTimes.current.length > 30) keyDownTimes.current.shift();

      // Calculate flight time (time between key releases)
      const flights: number[] = [];
      for (let i = 1; i < keyDownTimes.current.length; i++) {
        flights.push(keyDownTimes.current[i].down - keyDownTimes.current[i - 1].up);
      }
      const avgFlight = flights.length ? flights.reduce((s, f) => s + f, 0) / flights.length : 0;

      // WPM
      const elapsed = typingStartRef.current ? (Date.now() - typingStartRef.current) / 60000 : 0;
      const wpm = elapsed > 0 ? Math.round(wordCountRef.current / elapsed) : 0;

      setKeyMetrics({ wpm, dwell: Math.round(dwell), flight: Math.round(avgFlight) });
      delete keyTimes.current[e.key];
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, []);

  // ── Submit event ─────────────────────────────────────────────────────────
  const submitEvent = async (type: string, metrics: Record<string, unknown>) => {
    setSubmitting(s => ({ ...s, [type]: true }));
    try {
      const { data } = await behavioralApi.submitEvents([{ event_type: type, metrics }]);
      setBehaviorScore({
        behavior_score: data.behavior_score,
        is_anomalous: data.is_anomalous,
        anomaly_score: 0,
        method: "rule_based",
        component_scores: {},
        risk_flags: [],
      });
      setTotalSubmitted(t => t + 1);
      toast.success(`${type} event submitted — score: ${data.behavior_score.toFixed(0)}`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Submit failed");
    } finally {
      setSubmitting(s => ({ ...s, [type]: false }));
    }
  };

  // ── Auto-submit current tracked metrics ──────────────────────────────────
  const submitAutoMouse = () => {
    if (mouseMetrics.speed < 10) {
      toast.error("Move your mouse first to capture metrics");
      return;
    }
    submitEvent("mouse", {
      speed_pxps: mouseMetrics.speed,
      curvature: mouseMetrics.curvature,
      hesitation_rate: mouseMetrics.hesitation,
    });
  };

  const submitAutoKeyboard = () => {
    if (keyMetrics.wpm < 1) {
      toast.error("Type something on the keyboard first");
      return;
    }
    submitEvent("keyboard", {
      typing_speed_wpm: keyMetrics.wpm,
      dwell_time_ms: keyMetrics.dwell,
      flight_time_ms: keyMetrics.flight,
    });
  };

  // ── Profile query ─────────────────────────────────────────────────────────
  const { data: profile, isLoading: profileLoading, refetch } = useQuery<BehaviorProfileResult>({
    queryKey: ["behavior-profile"],
    queryFn: () => behavioralApi.getProfile().then(r => r.data),
    refetchInterval: totalSubmitted > 0 ? 5000 : false,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">Behavioral Biometrics</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
            Live mouse, keyboard & touch pattern analysis — anomaly detection via IsolationForest
          </p>
        </div>
        <button onClick={() => refetch()}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-[12px] font-medium transition-all"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.4)" }}>
          <RefreshCw size={12} />
          Refresh
        </button>
      </div>

      <div className="grid xl:grid-cols-[1fr,320px] gap-5">
        {/* LEFT — live tracking + manual sliders */}
        <div className="space-y-4">
          {/* Live tracking cards */}
          <div className="grid sm:grid-cols-2 gap-4">
            {/* Mouse */}
            <div className="rounded-2xl p-4 space-y-3"
              style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ background: "rgba(0,229,168,0.12)", border: "1px solid rgba(0,229,168,0.2)" }}>
                    <Mouse size={13} style={{ color: "#00E5A8" }} />
                  </div>
                  <span className="text-[12.5px] font-semibold text-white">Live Mouse</span>
                </div>
                <div className="w-1.5 h-1.5 rounded-full bg-[#00E5A8] animate-pulse" />
              </div>

              <div className="space-y-2">
                {[
                  { label: "Speed", value: `${mouseMetrics.speed} px/s`, score: Math.min(100, mouseMetrics.speed / 20), color: "#00E5A8" },
                  { label: "Curvature", value: mouseMetrics.curvature.toFixed(2), score: Math.min(100, mouseMetrics.curvature * 100), color: "#00C2FF" },
                  { label: "Hesitation", value: `${(mouseMetrics.hesitation * 100).toFixed(0)}%`, score: 100 - mouseMetrics.hesitation * 100, color: "#818cf8" },
                ].map(({ label, value, score, color }) => (
                  <div key={label}>
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-[rgba(255,255,255,0.35)]">{label}</span>
                      <span className="font-medium" style={{ color }}>{value}</span>
                    </div>
                    <ScoreBar score={score} color={color} />
                  </div>
                ))}
              </div>

              <button onClick={submitAutoMouse} disabled={submitting["mouse"]}
                className="w-full py-2 rounded-xl text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all"
                style={{ background: "rgba(0,229,168,0.1)", border: "1px solid rgba(0,229,168,0.2)", color: "#00E5A8", opacity: submitting["mouse"] ? 0.6 : 1 }}>
                {submitting["mouse"] ? <Loader2 size={10} className="animate-spin" /> : <Activity size={10} />}
                Submit Live Mouse Data
              </button>
            </div>

            {/* Keyboard */}
            <div className="rounded-2xl p-4 space-y-3"
              style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.2)" }}>
                    <Keyboard size={13} style={{ color: "#818cf8" }} />
                  </div>
                  <span className="text-[12.5px] font-semibold text-white">Live Keyboard</span>
                </div>
                <div className="w-1.5 h-1.5 rounded-full bg-[#818cf8] animate-pulse" />
              </div>

              {/* Type here box */}
              <textarea
                placeholder="Type here to capture keystroke dynamics…"
                rows={3}
                className="w-full rounded-xl px-3 py-2 text-[11px] text-white placeholder:text-[rgba(255,255,255,0.2)] resize-none outline-none"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}
              />

              <div className="space-y-2">
                {[
                  { label: "Typing Speed", value: `${keyMetrics.wpm} WPM`, score: Math.min(100, keyMetrics.wpm / 1.5), color: "#818cf8" },
                  { label: "Dwell Time", value: `${keyMetrics.dwell}ms`, score: keyMetrics.dwell > 50 && keyMetrics.dwell < 400 ? 80 : 30, color: "#00C2FF" },
                  { label: "Flight Time", value: `${keyMetrics.flight}ms`, score: keyMetrics.flight > 30 && keyMetrics.flight < 600 ? 80 : 30, color: "#f59e0b" },
                ].map(({ label, value, score, color }) => (
                  <div key={label}>
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-[rgba(255,255,255,0.35)]">{label}</span>
                      <span className="font-medium" style={{ color }}>{value}</span>
                    </div>
                    <ScoreBar score={score} color={color} />
                  </div>
                ))}
              </div>

              <button onClick={submitAutoKeyboard} disabled={submitting["keyboard"]}
                className="w-full py-2 rounded-xl text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all"
                style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)", color: "#818cf8", opacity: submitting["keyboard"] ? 0.6 : 1 }}>
                {submitting["keyboard"] ? <Loader2 size={10} className="animate-spin" /> : <Activity size={10} />}
                Submit Live Keyboard Data
              </button>
            </div>
          </div>

          {/* Manual slider inputs for touch */}
          <ModalityCard
            icon={Smartphone} label="Touch / Swipe Simulation" color="#f59e0b"
            score={behaviorScore?.component_scores?.["touch"] ?? null}
            submitting={submitting["touch"] ?? false}
            onSubmit={metrics => submitEvent("touch", metrics)}
            fields={[
              { key: "swipe_velocity", label: "Swipe Velocity", unit: " px/s", min: 50, max: 2000, step: 50, default: 500 },
              { key: "touch_pressure", label: "Touch Pressure", unit: "", min: 0.1, max: 1.0, step: 0.05, default: 0.5 },
              { key: "gesture_rhythm", label: "Gesture Rhythm", unit: "", min: 0.1, max: 5, step: 0.1, default: 1.2 },
            ]}
          />

          {/* Score result */}
          <AnimatePresence>
            {behaviorScore && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-2xl p-4"
                style={{
                  background: behaviorScore.is_anomalous ? "rgba(248,113,113,0.06)" : "rgba(0,229,168,0.06)",
                  border: `1px solid ${behaviorScore.is_anomalous ? "rgba(248,113,113,0.2)" : "rgba(0,229,168,0.2)"}`,
                }}
              >
                <div className="flex items-start gap-3">
                  <div className={cn(
                    "w-8 h-8 rounded-xl flex items-center justify-center shrink-0",
                    behaviorScore.is_anomalous ? "bg-[rgba(248,113,113,0.15)]" : "bg-[rgba(0,229,168,0.12)]"
                  )}>
                    {behaviorScore.is_anomalous
                      ? <AlertTriangle size={14} style={{ color: "#f87171" }} />
                      : <CheckCircle2 size={14} style={{ color: "#00E5A8" }} />
                    }
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[13px] font-semibold text-white">
                        {behaviorScore.is_anomalous ? "Anomaly Detected" : "Behavior Normal"}
                      </span>
                      <span className="text-[12px] font-bold"
                        style={{ color: behaviorScore.is_anomalous ? "#f87171" : "#00E5A8" }}>
                        {behaviorScore.behavior_score.toFixed(0)}/100
                      </span>
                    </div>
                    <div className="space-y-1 text-[11px]">
                      <div className="flex justify-between">
                        <span className="text-[rgba(255,255,255,0.35)]">Method</span>
                        <span className="text-white">{behaviorScore.method}</span>
                      </div>
                      {Object.entries(behaviorScore.component_scores).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-[rgba(255,255,255,0.35)] capitalize">{k} score</span>
                          <span className="font-medium" style={{ color: v >= 80 ? "#00E5A8" : v >= 60 ? "#f59e0b" : "#f87171" }}>
                            {v.toFixed(0)}
                          </span>
                        </div>
                      ))}
                    </div>
                    {behaviorScore.risk_flags.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {behaviorScore.risk_flags.slice(0, 4).map(f => (
                          <span key={f} className="px-1.5 py-0.5 rounded text-[9px]"
                            style={{ background: "rgba(248,113,113,0.12)", color: "#f87171" }}>
                            {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT — profile + info */}
        <div className="space-y-4">
          {/* Gauge + profile */}
          <div className="rounded-2xl p-5"
            style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-4">Behavior Score</p>

            {behaviorScore ? (
              <div className="flex flex-col items-center">
                <BehaviorGauge score={behaviorScore.behavior_score} />
                <div className="w-full mt-4 space-y-1.5 text-[11.5px]">
                  <div className="flex justify-between">
                    <span className="text-[rgba(255,255,255,0.35)]">Anomalous</span>
                    <span style={{ color: behaviorScore.is_anomalous ? "#f87171" : "#00E5A8" }}>
                      {behaviorScore.is_anomalous ? "Yes" : "No"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[rgba(255,255,255,0.35)]">Events submitted</span>
                    <span className="text-white">{totalSubmitted}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center py-6 gap-2">
                <BarChart3 size={28} style={{ color: "rgba(255,255,255,0.1)" }} />
                <p className="text-[11px] text-[rgba(255,255,255,0.2)] text-center">
                  Submit events to see your behavior score
                </p>
              </div>
            )}
          </div>

          {/* Baseline profile */}
          <div className="rounded-2xl p-4 space-y-3"
            style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="flex items-center justify-between">
              <p className="text-[12px] font-semibold text-white">Behavioral Baseline</p>
              {profileLoading && <Loader2 size={11} className="animate-spin text-[rgba(255,255,255,0.3)]" />}
            </div>

            {profile ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <div className={cn("w-2 h-2 rounded-full", profile.is_baseline_established ? "bg-[#00E5A8]" : "bg-[#f59e0b] animate-pulse")} />
                  <span className="text-[11px]" style={{ color: profile.is_baseline_established ? "#00E5A8" : "#f59e0b" }}>
                    {profile.is_baseline_established ? "Baseline established" : `Building baseline (${profile.total_events}/20 events)`}
                  </span>
                </div>

                {/* Progress to baseline */}
                {!profile.is_baseline_established && (
                  <div>
                    <div className="h-1.5 rounded-full bg-[rgba(255,255,255,0.05)]">
                      <div className="h-full rounded-full bg-[#f59e0b] transition-all"
                        style={{ width: `${(profile.total_events / 20) * 100}%` }} />
                    </div>
                    <p className="text-[9.5px] text-[rgba(255,255,255,0.2)] mt-1">
                      {20 - profile.total_events} more events needed for IsolationForest
                    </p>
                  </div>
                )}

                <div className="space-y-1.5 text-[11px]">
                  {[
                    { l: "Total Events", v: profile.total_events.toString() },
                    { l: "Avg Mouse Speed", v: profile.avg_mouse_speed ? `${profile.avg_mouse_speed.toFixed(0)} px/s` : "—" },
                    { l: "Avg Typing WPM", v: profile.avg_typing_speed_wpm ? `${profile.avg_typing_speed_wpm.toFixed(0)}` : "—" },
                    { l: "Avg Swipe Vel.", v: profile.avg_swipe_velocity ? `${profile.avg_swipe_velocity.toFixed(0)}` : "—" },
                    { l: "Profile Version", v: `v${profile.profile_version}` },
                  ].map(({ l, v }) => (
                    <div key={l} className="flex justify-between">
                      <span className="text-[rgba(255,255,255,0.35)]">{l}</span>
                      <span className="font-medium text-white">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-[11px] text-[rgba(255,255,255,0.2)]">No profile yet — submit events to build baseline</p>
            )}
          </div>

          {/* Phase info */}
          <div className="rounded-2xl p-4 space-y-3"
            style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.35)] uppercase tracking-wider">Detection Phases</p>
            {[
              { phase: "Phase 1", label: "Rule-Based", desc: "Human range validation for all metrics", active: true, color: "#00E5A8" },
              { phase: "Phase 2", label: "IsolationForest", desc: "Anomaly detection vs. your baseline (20+ events)", active: (profile?.total_events ?? 0) >= 20, color: "#00C2FF" },
              { phase: "Phase 3", label: "XGBoost", desc: "Supervised classification (roadmap)", active: false, color: "#818cf8" },
            ].map(({ phase, label, desc, active, color }) => (
              <div key={phase} className="flex items-start gap-2.5">
                <div className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", active ? "animate-none" : "opacity-25")}
                  style={{ background: active ? color : "rgba(255,255,255,0.2)" }} />
                <div>
                  <span className="text-[11px] font-semibold" style={{ color: active ? color : "rgba(255,255,255,0.25)" }}>
                    {phase} · {label}
                  </span>
                  <p className="text-[10px] text-[rgba(255,255,255,0.25)] mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
