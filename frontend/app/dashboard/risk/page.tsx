"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  ShieldAlert, AlertTriangle, Eye, Zap,
} from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";

const THREAT_EVENTS = Array.from({ length: 12 }, (_, i) => {
  const types = ["Spoof Attempt", "Deepfake Detected", "Replay Attack", "Abnormal Behavior", "Suspicious Device", "High-Risk Session"] as const;
  const colors = ["#f87171", "#f87171", "#fbbf24", "#fbbf24", "#818cf8", "#f87171"];
  const severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;
  const type = types[i % types.length];
  const color = colors[i % types.length];
  const severity = severities[i % 4];
  return {
    id: `thr_${Math.random().toString(36).slice(2, 8)}`,
    type, color, severity,
    userId: `usr_${Math.random().toString(36).slice(2, 6)}`,
    app: i % 2 === 0 ? "Campus Access System" : "Employee Attendance",
    score: 60 + Math.floor(Math.random() * 40),
    time: new Date(Date.now() - i * 1000 * 60 * (i * 3 + 1)).toLocaleTimeString(),
  };
});

const RISK_CHART = Array.from({ length: 14 }, (_, i) => ({
  date: new Date(Date.now() - (13 - i) * 86400000).toLocaleDateString("en", { month: "short", day: "numeric" }),
  Spoofs: Math.floor(Math.random() * 8),
  Deepfakes: Math.floor(Math.random() * 4),
  Replay: Math.floor(Math.random() * 6),
  Suspicious: Math.floor(Math.random() * 12),
}));

function ThreatTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl px-3 py-2.5 text-[11px] shadow-xl"
      style={{ background: "rgba(8,8,8,0.96)", border: "1px solid rgba(248,113,113,0.15)", backdropFilter: "blur(12px)" }}>
      <p className="text-[rgba(255,255,255,0.4)] mb-2 text-[10px]">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: p.color }} />
          <span style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></span>
        </p>
      ))}
    </div>
  );
}

const SEV_CFG = {
  CRITICAL: { color: "#f87171", bg: "rgba(248,113,113,0.1)",  border: "rgba(248,113,113,0.22)" },
  HIGH:     { color: "#f87171", bg: "rgba(248,113,113,0.07)", border: "rgba(248,113,113,0.15)" },
  MEDIUM:   { color: "#fbbf24", bg: "rgba(251,191,36,0.08)",  border: "rgba(251,191,36,0.18)" },
  LOW:      { color: "#818cf8", bg: "rgba(129,140,248,0.08)", border: "rgba(129,140,248,0.18)" },
};

export default function FraudCenterPage() {
  return (
    <div className="max-w-[1200px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <h1 className="text-[22px] font-semibold text-white tracking-tight">Fraud Center</h1>
            <span className="px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider uppercase"
              style={{ background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.25)", color: "#f87171" }}>
              THREAT INTELLIGENCE
            </span>
          </div>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)]">
            Real-time spoof detection, deepfake analysis, and threat monitoring.
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold"
          style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.2)", color: "#f87171" }}>
          <span className="status-dot-error" /> 3 Active Threats
        </div>
      </motion.div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Spoof Attempts",     value: "12",   color: "#f87171", icon: ShieldAlert },
          { label: "Deepfake Detections",value: "3",    color: "#f87171", icon: Eye },
          { label: "Replay Attacks",     value: "8",    color: "#fbbf24", icon: Zap },
          { label: "Suspicious Sessions",value: "21",   color: "#818cf8", icon: AlertTriangle },
        ].map((k, i) => (
          <motion.div key={k.label}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="dash-card p-4 rounded-2xl"
            style={{ borderColor: i < 2 ? "rgba(248,113,113,0.12)" : undefined }}>
            <div className="flex items-center justify-between mb-3">
              <p className="kpi-label">{k.label}</p>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{ background: `${k.color}12`, border: `1px solid ${k.color}20` }}>
                <k.icon size={12} style={{ color: k.color }} />
              </div>
            </div>
            <p className="text-[28px] font-bold" style={{ color: k.color }}>{k.value}</p>
            <p className="text-[10px] text-[rgba(255,255,255,0.28)] mt-1">Last 24 hours</p>
          </motion.div>
        ))}
      </div>

      {/* Threat Chart + Threat List */}
      <div className="grid xl:grid-cols-[1fr_380px] gap-4">
        {/* Chart */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="dash-card p-6 rounded-2xl"
          style={{ borderColor: "rgba(248,113,113,0.1)" }}>
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-[14px] font-semibold text-white">Threat Timeline</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">14-day threat event history</p>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={RISK_CHART} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
              <defs>
                {[["rs","#f87171"],["rd","#fbbf24"],["rr","#818cf8"],["rx","#f87171"]].map(([id, c]) => (
                  <linearGradient key={id} id={id} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={c} stopOpacity={0.2} />
                    <stop offset="95%" stopColor={c} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} width={20} />
              <Tooltip content={<ThreatTip />} />
              <Area type="monotone" dataKey="Spoofs"     name="Spoofs"     stroke="#f87171" strokeWidth={1.5} fill="url(#rs)" dot={false} />
              <Area type="monotone" dataKey="Deepfakes"  name="Deepfakes"  stroke="#fbbf24" strokeWidth={1.5} fill="url(#rd)" dot={false} />
              <Area type="monotone" dataKey="Replay"     name="Replay"     stroke="#818cf8" strokeWidth={1.5} fill="url(#rr)" dot={false} />
              <Area type="monotone" dataKey="Suspicious" name="Suspicious" stroke="#f87171" strokeWidth={1}   fill="url(#rx)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-4 mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            {[["#f87171","Spoofs"],["#fbbf24","Deepfakes"],["#818cf8","Replay"],["#f87171","Suspicious"]].map(([c,l]) => (
              <span key={l} className="flex items-center gap-1.5 text-[10.5px] text-[rgba(255,255,255,0.35)]">
                <span className="w-4 h-0.5 rounded-full" style={{ background: c }} />{l}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Threat Event List */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="dash-card p-5 rounded-2xl flex flex-col"
          style={{ borderColor: "rgba(248,113,113,0.1)" }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[14px] font-semibold text-white">Threat Events</h2>
            <span className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[9px] font-bold tracking-wider"
              style={{ background: "rgba(248,113,113,0.08)", border: "1px solid rgba(248,113,113,0.18)", color: "#f87171" }}>
              <span className="status-dot-error" /> LIVE
            </span>
          </div>
          <div className="space-y-1.5 overflow-y-auto flex-1" style={{ maxHeight: "340px" }}>
            {THREAT_EVENTS.map((ev, i) => {
              const sev = SEV_CFG[ev.severity];
              return (
                <motion.div key={ev.id}
                  initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex items-start gap-3 p-3 rounded-xl hover:bg-[rgba(255,255,255,0.02)] transition-all cursor-pointer">
                  <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                    style={{ background: `${ev.color}12`, border: `1px solid ${ev.color}20` }}>
                    <ShieldAlert size={11} style={{ color: ev.color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <p className="text-[12px] font-medium text-[rgba(255,255,255,0.8)] truncate">{ev.type}</p>
                      <span className="text-[8.5px] font-bold px-1.5 py-0.5 rounded-md tracking-wider shrink-0"
                        style={{ background: sev.bg, border: `1px solid ${sev.border}`, color: sev.color }}>
                        {ev.severity}
                      </span>
                    </div>
                    <p className="text-[10px] text-[rgba(255,255,255,0.28)] mt-0.5">
                      {ev.userId} · {ev.app}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-[10px] font-bold" style={{ color: ev.score >= 80 ? "#f87171" : "#fbbf24" }}>
                      {ev.score}
                    </p>
                    <p className="text-[9px] text-[rgba(255,255,255,0.22)]">{ev.time}</p>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
