"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { AppWindow, Plus, Search, ArrowUpRight, Key, Webhook, MoreHorizontal, Globe, Settings, Zap } from "lucide-react";
import Link from "next/link";

const MOCK_APPS = [
  {
    id: "app_01HX9Z",
    name: "Campus Access System",
    env: "Production",
    status: "active",
    owner: "Divye Bhatnagar",
    requests: "12,491",
    successRate: "98.2",
    latency: "52ms",
    created: "Jan 12, 2025",
    lastActivity: "Just now",
    enrollmentCount: 3240,
    verificationCount: 9251,
  },
  {
    id: "app_02KY1A",
    name: "Employee Attendance",
    env: "Production",
    status: "active",
    owner: "Divye Bhatnagar",
    requests: "5,832",
    successRate: "99.1",
    latency: "48ms",
    created: "Feb 3, 2025",
    lastActivity: "2 min ago",
    enrollmentCount: 1840,
    verificationCount: 3992,
  },
  {
    id: "app_03LZ2B",
    name: "Identity Verification",
    env: "Staging",
    status: "active",
    owner: "Divye Bhatnagar",
    requests: "1,204",
    successRate: "94.7",
    latency: "89ms",
    created: "Mar 18, 2025",
    lastActivity: "1 hour ago",
    enrollmentCount: 340,
    verificationCount: 864,
  },
  {
    id: "app_04MQ3C",
    name: "Customer KYC",
    env: "Development",
    status: "inactive",
    owner: "Divye Bhatnagar",
    requests: "0",
    successRate: "—",
    latency: "—",
    created: "Jun 10, 2025",
    lastActivity: "Never",
    enrollmentCount: 0,
    verificationCount: 0,
  },
];

function EnvBadge({ env }: { env: string }) {
  const cfg = {
    Production:  { color: "#00E5A8", bg: "rgba(0,229,168,0.08)",  border: "rgba(0,229,168,0.18)" },
    Staging:     { color: "#fbbf24", bg: "rgba(251,191,36,0.08)",  border: "rgba(251,191,36,0.2)" },
    Development: { color: "#818cf8", bg: "rgba(129,140,248,0.08)", border: "rgba(129,140,248,0.18)" },
  }[env] ?? { color: "rgba(255,255,255,0.4)", bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.1)" };
  return (
    <span className="px-2 py-0.5 rounded-full text-[9.5px] font-semibold tracking-wide uppercase"
      style={{ background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}>
      {env}
    </span>
  );
}

export default function ApplicationsPage() {
  const [search, setSearch] = useState("");
  const filtered = MOCK_APPS.filter(a =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.env.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="max-w-[1200px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-[22px] font-semibold text-white tracking-tight">Applications</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)] mt-1">
            Manage your NeoFace-integrated applications and their API usage.
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 rounded-xl text-[12.5px] font-semibold transition-all"
          style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,194,255,0.16)")}
          onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,194,255,0.1)")}>
          <Plus size={13} /> New Application
        </button>
      </motion.div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Total Apps",      value: "4",        color: "#00C2FF" },
          { label: "Active",          value: "3",        color: "#00E5A8" },
          { label: "Total Requests",  value: "19,527",   color: "#818cf8" },
          { label: "Avg Success Rate",value: "97.3%",    color: "#fbbf24" },
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

      {/* Search */}
      <div className="relative">
        <Search size={13} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[rgba(255,255,255,0.25)]" />
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search applications..."
          className="w-full pl-9 pr-4 py-2.5 rounded-xl text-[13px] text-[rgba(255,255,255,0.7)] outline-none transition-all"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
          onFocus={e => (e.currentTarget.style.borderColor = "rgba(0,194,255,0.25)")}
          onBlur={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)")}
        />
      </div>

      {/* App Cards */}
      <div className="grid md:grid-cols-2 gap-4">
        {filtered.map((app, i) => (
          <motion.div key={app.id}
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.09 }}
            className="dash-card rounded-2xl p-6 group hover:border-[rgba(0,194,255,0.14)] transition-all cursor-pointer"
          >
            {/* Card header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: "rgba(0,194,255,0.08)", border: "1px solid rgba(0,194,255,0.15)" }}>
                  <AppWindow size={18} style={{ color: "#00C2FF" }} />
                </div>
                <div>
                  <p className="text-[14px] font-semibold text-white leading-tight">{app.name}</p>
                  <p className="text-[10.5px] text-[rgba(255,255,255,0.28)] font-mono mt-0.5">{app.id}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <EnvBadge env={app.env} />
                <button className="w-7 h-7 flex items-center justify-center rounded-lg transition-all text-[rgba(255,255,255,0.3)] hover:text-white hover:bg-[rgba(255,255,255,0.06)]">
                  <MoreHorizontal size={14} />
                </button>
              </div>
            </div>

            {/* Status */}
            <div className="flex items-center gap-1.5 mb-5">
              {app.status === "active"
                ? <><span className="status-dot-live" /><span className="text-[10.5px] text-[#00E5A8]">Active</span></>
                : <><span className="w-1.5 h-1.5 rounded-full bg-[rgba(255,255,255,0.2)]" /><span className="text-[10.5px] text-[rgba(255,255,255,0.3)]">Inactive</span></>}
              <span className="text-[rgba(255,255,255,0.15)] mx-1">·</span>
              <span className="text-[10.5px] text-[rgba(255,255,255,0.28)]">Last active: {app.lastActivity}</span>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-3 mb-5">
              {[
                { label: "Requests",  value: app.requests,     color: "#00C2FF" },
                { label: "Success",   value: app.successRate === "—" ? "—" : `${app.successRate}%`, color: app.successRate !== "—" ? "#00E5A8" : "rgba(255,255,255,0.25)" },
                { label: "Latency",   value: app.latency,      color: "#fbbf24" },
              ].map(m => (
                <div key={m.label} className="p-3 rounded-xl text-center"
                  style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)" }}>
                  <p className="text-[15px] font-bold mb-0.5" style={{ color: m.color }}>{m.value}</p>
                  <p className="text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.25)] font-medium">{m.label}</p>
                </div>
              ))}
            </div>

            {/* Progress bar */}
            {app.successRate !== "—" && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-[rgba(255,255,255,0.28)]">Success rate</span>
                  <span className="text-[10px] font-semibold" style={{ color: "#00E5A8" }}>{app.successRate}%</span>
                </div>
                <div className="h-1 rounded-full" style={{ background: "rgba(255,255,255,0.07)" }}>
                  <div className="h-full rounded-full" style={{
                    width: `${app.successRate}%`,
                    background: "linear-gradient(90deg, #00E5A8, #00C2FF)",
                  }} />
                </div>
              </div>
            )}

            {/* Footer actions */}
            <div className="flex items-center gap-2 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
              <button className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-medium transition-all text-[rgba(255,255,255,0.45)] hover:text-white"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <Key size={10} /> API Keys
              </button>
              <button className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-medium transition-all text-[rgba(255,255,255,0.45)] hover:text-white"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <Webhook size={10} /> Webhooks
              </button>
              <button className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-medium transition-all text-[rgba(0,194,255,0.7)] hover:text-[#00C2FF]"
                style={{ background: "rgba(0,194,255,0.05)", border: "1px solid rgba(0,194,255,0.12)" }}>
                <Zap size={10} /> Analytics <ArrowUpRight size={9} />
              </button>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
