"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Key, Plus, Copy, RotateCcw, Trash2, Eye, EyeOff, Shield, AlertTriangle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

const MOCK_KEYS = [
  {
    id: "key_live_nf_01",
    name: "Production — Campus Access",
    prefix: "nf_live_jK9x",
    env: "Production",
    scope: ["enrollment:write", "verification:read", "liveness:read"],
    created: "Jan 12, 2025",
    lastUsed: "Just now",
    requests: "124,491",
    status: "active",
  },
  {
    id: "key_live_nf_02",
    name: "Production — Attendance System",
    prefix: "nf_live_mP2y",
    env: "Production",
    scope: ["enrollment:read", "verification:read"],
    created: "Feb 3, 2025",
    lastUsed: "2 min ago",
    requests: "58,320",
    status: "active",
  },
  {
    id: "key_test_nf_03",
    name: "Staging — Identity Verification",
    prefix: "nf_test_qR8z",
    env: "Staging",
    scope: ["enrollment:write", "verification:write", "liveness:write", "session:write"],
    created: "Mar 18, 2025",
    lastUsed: "1 hour ago",
    requests: "12,041",
    status: "active",
  },
  {
    id: "key_test_nf_04",
    name: "Dev — Customer KYC Testing",
    prefix: "nf_test_aB5w",
    env: "Development",
    scope: ["verification:read"],
    created: "Jun 10, 2025",
    lastUsed: "Never",
    requests: "0",
    status: "inactive",
  },
];

const SCOPE_COLORS: Record<string, string> = {
  "enrollment:write": "#00E5A8",
  "enrollment:read":  "#00C2FF",
  "verification:write": "#818cf8",
  "verification:read":  "#818cf8",
  "liveness:write":   "#fbbf24",
  "liveness:read":    "#fbbf24",
  "session:write":    "#f87171",
};

const ENV_CFG: Record<string, { color: string; bg: string; border: string }> = {
  Production:  { color: "#00E5A8", bg: "rgba(0,229,168,0.08)",  border: "rgba(0,229,168,0.18)" },
  Staging:     { color: "#fbbf24", bg: "rgba(251,191,36,0.08)",  border: "rgba(251,191,36,0.2)" },
  Development: { color: "#818cf8", bg: "rgba(129,140,248,0.08)", border: "rgba(129,140,248,0.18)" },
};

export default function ApiKeysPage() {
  const [showNew, setShowNew] = useState(false);
  const [revealId, setRevealId] = useState<string | null>(null);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyEnv, setNewKeyEnv] = useState("Production");

  const handleCopy = (prefix: string) => {
    navigator.clipboard.writeText(`${prefix}••••••••••••••••••••••••••••`);
    toast.success("Copied to clipboard");
  };

  return (
    <div className="max-w-[960px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-[22px] font-semibold text-white tracking-tight">API Keys</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)] mt-1">
            Manage authentication credentials for your applications.
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-[12.5px] font-semibold transition-all"
          style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,194,255,0.16)")}
          onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,194,255,0.1)")}>
          <Plus size={13} /> Generate API Key
        </button>
      </motion.div>

      {/* Warning banner */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}
        className="flex items-start gap-3 px-4 py-3 rounded-xl"
        style={{ background: "rgba(251,191,36,0.06)", border: "1px solid rgba(251,191,36,0.15)" }}>
        <AlertTriangle size={14} style={{ color: "#fbbf24" }} className="mt-0.5 shrink-0" />
        <p className="text-[12px] text-[rgba(255,255,255,0.55)] leading-relaxed">
          <strong className="text-[rgba(251,191,36,0.9)]">Security notice:</strong> API keys grant full access to your NeoFace account.
          Store them securely and never expose them in client-side code or public repositories.
        </p>
      </motion.div>

      {/* New key modal */}
      {showNew && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="dash-card p-6 rounded-2xl"
          style={{ borderColor: "rgba(0,194,255,0.2)" }}>
          <h3 className="text-[14px] font-semibold text-white mb-4">Create new API key</h3>
          <div className="grid sm:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-[11px] text-[rgba(255,255,255,0.4)] font-medium uppercase tracking-wide block mb-1.5">Key name</label>
              <input
                value={newKeyName} onChange={e => setNewKeyName(e.target.value)}
                placeholder="e.g. Production — Mobile App"
                className="w-full px-3.5 py-2.5 rounded-xl text-[13px] text-white outline-none"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)" }}
                onFocus={e => (e.currentTarget.style.borderColor = "rgba(0,194,255,0.35)")}
                onBlur={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")}
              />
            </div>
            <div>
              <label className="text-[11px] text-[rgba(255,255,255,0.4)] font-medium uppercase tracking-wide block mb-1.5">Environment</label>
              <select
                value={newKeyEnv} onChange={e => setNewKeyEnv(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl text-[13px] text-white outline-none"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)" }}>
                <option>Production</option>
                <option>Staging</option>
                <option>Development</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => { setShowNew(false); toast.success("API key created — save it now, it won't be shown again."); }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-[12.5px] font-semibold"
              style={{ background: "rgba(0,194,255,0.12)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}>
              <Key size={12} /> Generate key
            </button>
            <button onClick={() => setShowNew(false)}
              className="px-4 py-2 rounded-xl text-[12.5px] font-medium text-[rgba(255,255,255,0.35)]"
              style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
              Cancel
            </button>
          </div>
        </motion.div>
      )}

      {/* Keys list */}
      <div className="space-y-3">
        {MOCK_KEYS.map((key, i) => {
          const envCfg = ENV_CFG[key.env];
          return (
            <motion.div key={key.id}
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.08 }}
              className="dash-card rounded-2xl p-5 group"
            >
              <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                    style={{ background: `${envCfg.color}10`, border: `1px solid ${envCfg.color}20` }}>
                    <Key size={15} style={{ color: envCfg.color }} />
                  </div>
                  <div>
                    <p className="text-[13.5px] font-semibold text-white">{key.name}</p>
                    <p className="text-[10px] text-[rgba(255,255,255,0.28)] font-mono mt-0.5">{key.id}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-full text-[9.5px] font-semibold uppercase tracking-wide"
                    style={{ background: envCfg.bg, border: `1px solid ${envCfg.border}`, color: envCfg.color }}>
                    {key.env}
                  </span>
                  {key.status === "active"
                    ? <span className="flex items-center gap-1 text-[10px]" style={{ color: "#00E5A8" }}><span className="status-dot-live" /> Active</span>
                    : <span className="flex items-center gap-1 text-[10px] text-[rgba(255,255,255,0.3)]">○ Inactive</span>}
                </div>
              </div>

              {/* Key preview */}
              <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl mb-4"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", fontFamily: "monospace" }}>
                <Shield size={11} style={{ color: "rgba(255,255,255,0.25)" }} />
                <span className="text-[12px] text-[rgba(255,255,255,0.55)] flex-1 truncate">
                  {revealId === key.id
                    ? `${key.prefix}••••••••••••••••••••••••••••`
                    : `${key.prefix}${"•".repeat(28)}`}
                </span>
                <button onClick={() => setRevealId(revealId === key.id ? null : key.id)}
                  className="text-[rgba(255,255,255,0.3)] hover:text-white transition-colors">
                  {revealId === key.id ? <EyeOff size={12} /> : <Eye size={12} />}
                </button>
                <button onClick={() => handleCopy(key.prefix)}
                  className="text-[rgba(255,255,255,0.3)] hover:text-white transition-colors ml-1">
                  <Copy size={12} />
                </button>
              </div>

              {/* Scope badges */}
              <div className="flex flex-wrap gap-1.5 mb-4">
                {key.scope.map(s => (
                  <span key={s} className="text-[9.5px] font-mono px-2 py-0.5 rounded-md"
                    style={{
                      background: `${SCOPE_COLORS[s] ?? "#fff"}10`,
                      border: `1px solid ${SCOPE_COLORS[s] ?? "#fff"}18`,
                      color: SCOPE_COLORS[s] ?? "rgba(255,255,255,0.45)",
                    }}>
                    {s}
                  </span>
                ))}
              </div>

              {/* Metadata + actions */}
              <div className="flex items-center justify-between flex-wrap gap-3 pt-3"
                style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                <div className="flex items-center gap-4 text-[10.5px] text-[rgba(255,255,255,0.28)]">
                  <span>Created {key.created}</span>
                  <span>·</span>
                  <span>Last used: {key.lastUsed}</span>
                  <span>·</span>
                  <span>{key.requests} requests</span>
                </div>
                <div className="flex items-center gap-2">
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10.5px] font-medium text-[rgba(255,255,255,0.4)] hover:text-white transition-all"
                    style={{ border: "1px solid rgba(255,255,255,0.07)" }}
                    onClick={() => toast.info("Key rotation coming soon")}>
                    <RotateCcw size={10} /> Rotate
                  </button>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10.5px] font-medium transition-all"
                    style={{ border: "1px solid rgba(248,113,113,0.15)", color: "rgba(248,113,113,0.6)" }}
                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(248,113,113,0.08)"; }}
                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                    onClick={() => toast.error("Revoke key coming soon")}>
                    <Trash2 size={10} /> Revoke
                  </button>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
