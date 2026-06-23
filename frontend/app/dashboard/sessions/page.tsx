"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  Activity, CheckCircle2, XCircle, Clock, Search, Filter,
  Shield, Fingerprint, Scan, Eye, AlertTriangle, ArrowUpRight, ChevronDown,
} from "lucide-react";

const SESSION_TYPES = [
  { value: "all",       label: "All Events" },
  { value: "verified",  label: "Verified" },
  { value: "failed",    label: "Failed" },
  { value: "liveness",  label: "Liveness" },
  { value: "enrolled",  label: "Enrolled" },
];

const MOCK_SESSIONS = Array.from({ length: 20 }, (_, i) => {
  const types = ["verified", "failed", "liveness", "enrolled", "suspicious"] as const;
  const type = types[i % types.length];
  const apps = ["Campus Access System", "Employee Attendance", "Identity Verification"];
  const modalities = ["face", "iris", "fingerprint"];
  const devices = ["iPhone 15 Pro", "Galaxy S24", "Pixel 8", "Chrome / macOS", "Safari / iOS"];
  return {
    id: `ses_${Math.random().toString(36).slice(2, 10)}`,
    type,
    userId: `usr_${Math.random().toString(36).slice(2, 8)}`,
    app: apps[i % apps.length],
    modality: modalities[i % modalities.length],
    device: devices[i % devices.length],
    ip: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
    latency: `${40 + Math.floor(Math.random() * 120)}ms`,
    riskScore: type === "suspicious" ? Math.floor(70 + Math.random() * 25) : Math.floor(Math.random() * 25),
    timestamp: new Date(Date.now() - i * 1000 * 60 * (i + 1)).toLocaleTimeString(),
    date: new Date(Date.now() - i * 1000 * 60 * (i + 1)).toLocaleDateString(),
  };
});

const TYPE_CFG = {
  verified:   { icon: CheckCircle2, color: "#00E5A8", label: "Verified",   bg: "rgba(0,229,168,0.08)" },
  failed:     { icon: XCircle,      color: "#f87171", label: "Failed",     bg: "rgba(248,113,113,0.08)" },
  liveness:   { icon: Scan,         color: "#818cf8", label: "Liveness",   bg: "rgba(129,140,248,0.08)" },
  enrolled:   { icon: Fingerprint,  color: "#00C2FF", label: "Enrolled",   bg: "rgba(0,194,255,0.08)" },
  suspicious: { icon: AlertTriangle,color: "#fbbf24", label: "Suspicious", bg: "rgba(251,191,36,0.08)" },
};

function RiskBadge({ score }: { score: number }) {
  const cfg = score >= 70 ? { color: "#f87171", label: "HIGH" }
    : score >= 40 ? { color: "#fbbf24", label: "MED" }
    : { color: "#00E5A8", label: "LOW" };
  return (
    <span className="text-[9px] font-bold tracking-wider px-1.5 py-0.5 rounded-md"
      style={{ background: `${cfg.color}12`, color: cfg.color, border: `1px solid ${cfg.color}20` }}>
      {cfg.label} {score}
    </span>
  );
}

export default function SessionsPage() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");

  const filtered = MOCK_SESSIONS.filter(s => {
    const matchType = typeFilter === "all" || s.type === typeFilter;
    const matchSearch = !search || s.id.includes(search) || s.userId.includes(search) || s.app.toLowerCase().includes(search.toLowerCase());
    return matchType && matchSearch;
  });

  return (
    <div className="max-w-[1200px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-[22px] font-semibold text-white tracking-tight">Authentication Sessions</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)] mt-1">
            Real-time stream of all authentication events across your applications.
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold"
          style={{ background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.15)", color: "#00E5A8" }}>
          <span className="status-dot-live" /> LIVE
        </div>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total Sessions",  value: "2,491",  color: "#00C2FF" },
          { label: "Verified",        value: "2,312",  color: "#00E5A8" },
          { label: "Failed",          value: "149",    color: "#f87171" },
          { label: "Suspicious",      value: "30",     color: "#fbbf24" },
        ].map((s, i) => (
          <motion.div key={s.label}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="dash-card p-4 rounded-2xl">
            <p className="kpi-label mb-2">{s.label}</p>
            <p className="text-[24px] font-bold" style={{ color: s.color }}>{s.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[rgba(255,255,255,0.25)]" />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by session ID, user ID, or app…"
            className="w-full pl-9 pr-4 py-2.5 rounded-xl text-[12.5px] text-[rgba(255,255,255,0.7)] outline-none transition-all"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)" }}
            onFocus={e => (e.currentTarget.style.borderColor = "rgba(0,194,255,0.25)")}
            onBlur={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)")}
          />
        </div>
        <div className="flex items-center gap-1.5 rounded-xl p-1"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
          {SESSION_TYPES.map(t => (
            <button key={t.value}
              onClick={() => setTypeFilter(t.value)}
              className="px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all"
              style={{
                background: typeFilter === t.value ? "rgba(255,255,255,0.08)" : "transparent",
                color: typeFilter === t.value ? "#fff" : "rgba(255,255,255,0.38)",
                border: typeFilter === t.value ? "1px solid rgba(255,255,255,0.1)" : "1px solid transparent",
              }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sessions table */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
        className="dash-card rounded-2xl overflow-hidden">
        <div className="px-5 py-3.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <p className="text-[11.5px] text-[rgba(255,255,255,0.35)]">
            Showing {filtered.length} sessions
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Event</th>
                <th>Session ID</th>
                <th>User</th>
                <th>Application</th>
                <th>Modality</th>
                <th>Device</th>
                <th>Latency</th>
                <th>Risk</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => {
                const cfg = TYPE_CFG[s.type];
                return (
                  <motion.tr key={s.id}
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.02 }}
                    className="cursor-pointer">
                    <td>
                      <span className="flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-md flex items-center justify-center"
                          style={{ background: cfg.bg, border: `1px solid ${cfg.color}20` }}>
                          <cfg.icon size={10} style={{ color: cfg.color }} />
                        </span>
                        <span className="text-[11.5px] font-medium" style={{ color: cfg.color }}>{cfg.label}</span>
                      </span>
                    </td>
                    <td><span className="font-mono text-[11px] text-[rgba(255,255,255,0.4)]">{s.id}</span></td>
                    <td><span className="font-mono text-[11px]">{s.userId}</span></td>
                    <td className="max-w-[140px]"><span className="truncate block text-[11.5px]">{s.app}</span></td>
                    <td>
                      <span className="flex items-center gap-1 text-[11px] font-medium capitalize">
                        {s.modality === "face" ? <Scan size={10} style={{ color: "#00E5A8" }} />
                          : s.modality === "iris" ? <Eye size={10} style={{ color: "#00C2FF" }} />
                          : <Fingerprint size={10} style={{ color: "#818cf8" }} />}
                        {s.modality}
                      </span>
                    </td>
                    <td><span className="text-[11px] text-[rgba(255,255,255,0.4)]">{s.device}</span></td>
                    <td><span className="font-mono text-[11px]">{s.latency}</span></td>
                    <td><RiskBadge score={s.riskScore} /></td>
                    <td>
                      <div>
                        <p className="text-[11px]">{s.timestamp}</p>
                        <p className="text-[9.5px] text-[rgba(255,255,255,0.25)]">{s.date}</p>
                      </div>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
