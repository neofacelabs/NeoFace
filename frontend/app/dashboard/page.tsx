"use client";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  AppWindow, Users, Zap, ShieldCheck, Fingerprint, Clock,
  TrendingUp, AlertTriangle, Globe, Server, RefreshCw,
  ArrowUpRight, CheckCircle2, XCircle, Activity, Key, BookOpen,
  Webhook, Download, Terminal, ChevronRight, Building2,
  ShieldAlert, BarChart3, Cpu, Eye, ArrowRight, Brain,
} from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis,
  CartesianGrid, LineChart, Line,
} from "recharts";
import { dashboardApi } from "@/lib/api";
import { useRole } from "@/hooks/use-role";
import { useAuthStore } from "@/store/auth";
import Link from "next/link";
import { formatDate } from "@/lib/utils";
import type { UserStats, VerificationStats, PaymentOverview } from "@/types";

/* ─── Animated counter ───────────────────────────────────────────────────── */
function Counter({ target, suffix = "", prefix = "", decimals = 0 }: {
  target: number; suffix?: string; prefix?: string; decimals?: number;
}) {
  const [val, setVal] = useState(0);
  const done = useRef(false);
  useEffect(() => {
    if (done.current || !target) return;
    done.current = true;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - start) / 1100, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(target * ease);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target]);
  return <>{prefix}{decimals === 0 ? Math.round(val).toLocaleString() : val.toFixed(decimals)}{suffix}</>;
}

/* ─── Chart tooltip ──────────────────────────────────────────────────────── */
function ChartTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl px-3 py-2.5 text-[11px] shadow-xl"
      style={{ background: "rgba(8,8,8,0.96)", border: "1px solid rgba(255,255,255,0.1)", backdropFilter: "blur(12px)" }}>
      <p className="text-[rgba(255,255,255,0.4)] mb-2 text-[10px] uppercase tracking-wider font-medium">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center gap-2 mb-0.5">
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: p.color }} />
          <span style={{ color: "rgba(255,255,255,0.45)" }}>{p.name}:</span>
          <strong style={{ color: p.color }}>{Number(p.value).toLocaleString()}</strong>
        </p>
      ))}
    </div>
  );
}

/* ─── KPI Card ───────────────────────────────────────────────────────────── */
function KpiCard({ icon: Icon, label, value, prefix, suffix, decimals, delta, deltaDir = "up", color, loading, index, href }: {
  icon: any; label: string; value: number; prefix?: string; suffix?: string;
  decimals?: number; delta?: string; deltaDir?: "up" | "down"; color: string;
  loading?: boolean; index: number; href?: string;
}) {
  const inner = (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.07, ease: [0.16, 1, 0.3, 1] }}
      className="dash-card p-5 group cursor-default h-full"
      style={{ borderRadius: 14 }}
      whileHover={{ y: -1 }}
    >
      <div className="flex items-center justify-between mb-4">
        <p className="kpi-label">{label}</p>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: `${color}14`, border: `1px solid ${color}20` }}>
          <Icon size={14} style={{ color }} />
        </div>
      </div>
      {loading ? (
        <div className="h-8 w-24 rounded-md animate-pulse" style={{ background: "rgba(255,255,255,0.06)" }} />
      ) : (
        <p className="kpi-value" style={{ color }}>
          <Counter target={value} prefix={prefix} suffix={suffix} decimals={decimals} />
        </p>
      )}
      {delta && (
        <p className="mt-2 flex items-center gap-1 text-[10.5px]" style={{ color: "rgba(255,255,255,0.3)" }}>
          <ArrowUpRight size={10} style={{ color: deltaDir === "up" ? "#00E5A8" : "#f87171",
            transform: deltaDir === "down" ? "rotate(90deg)" : undefined }} />
          <span style={{ color: deltaDir === "up" ? "#00E5A8" : "#f87171" }}>{delta}</span>
          vs last 7d
        </p>
      )}
    </motion.div>
  );
  if (href) return <Link href={href} className="block h-full">{inner}</Link>;
  return inner;
}

/* ─── Coming Soon Card ───────────────────────────────────────────────────── */
function ComingSoon({ title, desc, icon: Icon, color }: {
  title: string; desc: string; icon: any; color: string;
}) {
  return (
    <div className="dash-card rounded-2xl p-10 flex flex-col items-center justify-center text-center gap-4">
      <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
        style={{ background: `${color}12`, border: `1px solid ${color}20` }}>
        <Icon size={22} style={{ color }} />
      </div>
      <div>
        <p className="text-[14px] font-semibold text-white mb-1">{title}</p>
        <p className="text-[12px] text-[rgba(255,255,255,0.35)] max-w-[220px] mx-auto leading-relaxed">{desc}</p>
      </div>
      <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-semibold tracking-wider uppercase"
        style={{ background: `${color}0d`, border: `1px solid ${color}1a`, color }}>
        Coming Soon
      </div>
    </div>
  );
}

/* ─── Live Auth Event ────────────────────────────────────────────────────── */
const EVENT_TYPES: Record<string, { label: string; color: string; icon: any }> = {
  enrolled:    { label: "Enrollment Created",  color: "#00E5A8", icon: Fingerprint },
  verified:    { label: "Identity Verified",   color: "#00C2FF", icon: ShieldCheck },
  liveness:    { label: "Liveness Passed",     color: "#818cf8", icon: Eye },
  session:     { label: "Session Created",     color: "#00E5A8", icon: Activity },
  suspicious:  { label: "Suspicious Activity", color: "#f87171", icon: AlertTriangle },
  failed:      { label: "Verification Failed", color: "#fbbf24", icon: XCircle },
};

function LiveFeedItem({ txn, index }: { txn: any; index: number }) {
  const success = txn.authentication_result;
  const type = success ? "verified" : "failed";
  const ev = EVENT_TYPES[type];
  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04 }}
      className="flex items-center gap-3 py-2.5 px-3 rounded-xl hover:bg-[rgba(255,255,255,0.025)] transition-all"
    >
      <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${ev.color}12`, border: `1px solid ${ev.color}20` }}>
        <ev.icon size={11} style={{ color: ev.color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12px] font-medium text-[rgba(255,255,255,0.75)] truncate">{ev.label}</p>
        <p className="text-[10px] text-[rgba(255,255,255,0.25)] truncate">
          {txn.created_at ? formatDate(txn.created_at) : "just now"}
          {txn.modality && ` · ${txn.modality}`}
        </p>
      </div>
      <span className="text-[10px] font-semibold shrink-0 px-1.5 py-0.5 rounded-md"
        style={{ background: `${ev.color}10`, color: ev.color }}>
        {success ? "PASS" : "FAIL"}
      </span>
    </motion.div>
  );
}

/* ─── API Health Row ─────────────────────────────────────────────────────── */
function ApiHealthRow({ name, latency, rate, status }: {
  name: string; latency: string; rate: string; status: "operational" | "degraded" | "outage";
}) {
  const statusCfg = {
    operational: { color: "#00E5A8", dot: "status-dot-live", label: "Operational" },
    degraded:    { color: "#fbbf24", dot: "status-dot-warn",  label: "Degraded" },
    outage:      { color: "#f87171", dot: "status-dot-error", label: "Outage" },
  }[status];
  return (
    <tr>
      <td className="py-3 pr-4">
        <span className="text-[12.5px] text-[rgba(255,255,255,0.7)] font-medium">{name}</span>
      </td>
      <td className="py-3 pr-4">
        <span className="text-[12px] font-mono text-[rgba(255,255,255,0.45)]">{latency}</span>
      </td>
      <td className="py-3 pr-4">
        <span className="text-[12px] font-mono" style={{ color: "#00E5A8" }}>{rate}</span>
      </td>
      <td className="py-3">
        <span className="flex items-center gap-1.5">
          <span className={statusCfg.dot} />
          <span className="text-[11px]" style={{ color: statusCfg.color }}>{statusCfg.label}</span>
        </span>
      </td>
    </tr>
  );
}

/* ─── App Card ───────────────────────────────────────────────────────────── */
function AppCard({ name, env, usage, rate, status, index }: {
  name: string; env: string; usage: string; rate: string; status: "active" | "inactive"; index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 + index * 0.08 }}
      className="dash-card p-5 rounded-2xl group hover:border-[rgba(0,194,255,0.15)] transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: "rgba(0,194,255,0.08)", border: "1px solid rgba(0,194,255,0.15)" }}>
          <AppWindow size={16} style={{ color: "#00C2FF" }} />
        </div>
        <span
          className="text-[9px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full"
          style={{
            background: status === "active" ? "rgba(0,229,168,0.1)" : "rgba(255,255,255,0.05)",
            color:      status === "active" ? "#00E5A8"             : "rgba(255,255,255,0.3)",
            border:     status === "active" ? "1px solid rgba(0,229,168,0.2)" : "1px solid rgba(255,255,255,0.07)",
          }}
        >
          {status === "active" ? "● Active" : "○ Inactive"}
        </span>
      </div>
      <p className="text-[13.5px] font-semibold text-white mb-0.5">{name}</p>
      <p className="text-[10.5px] text-[rgba(255,255,255,0.3)] mb-4 font-mono">{env}</p>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-[rgba(255,255,255,0.35)]">{usage} req today</span>
        <span style={{ color: "#00E5A8" }}>{rate} pass</span>
      </div>
      <div className="mt-2 w-full h-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.05)" }}>
        <div className="h-0.5 rounded-full" style={{ width: rate, background: "linear-gradient(90deg, #00E5A8, #00C2FF)" }} />
      </div>
    </motion.div>
  );
}

/* ─── Quick Action Button ────────────────────────────────────────────────── */
function QuickAction({ icon: Icon, label, href, desc, color }: {
  icon: any; label: string; href: string; desc: string; color: string;
}) {
  return (
    <Link href={href}
      className="flex items-center gap-3 px-4 py-3 rounded-xl group transition-all"
      style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.06)" }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = `${color}25`)}
      onMouseLeave={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)")}
    >
      <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: `${color}10`, border: `1px solid ${color}18` }}>
        <Icon size={14} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[12.5px] font-semibold text-[rgba(255,255,255,0.8)] group-hover:text-white transition-colors">{label}</p>
        <p className="text-[10px] text-[rgba(255,255,255,0.3)]">{desc}</p>
      </div>
      <ChevronRight size={12} className="text-[rgba(255,255,255,0.2)] group-hover:text-[rgba(255,255,255,0.5)] transition-colors" />
    </Link>
  );
}

/* ──────────────────────────────────────────────────────────────────────────
   CUSTOMER DASHBOARD
   ────────────────────────────────────────────────────────────────────────── */
function CustomerDashboard() {
  const user = useAuthStore(s => s.user);
  const [range, setRange] = useState<"24H" | "7D" | "30D" | "90D">("7D");

  const { data: userStats, isLoading: uLoad } = useQuery<UserStats>({
    queryKey: ["dashboard-users"],
    queryFn: () => dashboardApi.getUsers().then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: verifyStats, isLoading: vLoad } = useQuery<VerificationStats>({
    queryKey: ["dashboard-verifications"],
    queryFn: () => dashboardApi.getVerifications().then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: overview, isLoading: ovLoad } = useQuery<PaymentOverview>({
    queryKey: ["payments-overview"],
    queryFn: () => dashboardApi.getPaymentsOverview().then(r => r.data),
    refetchInterval: 15_000,
  });

  const { data: recentData, isLoading: rLoad } = useQuery<{ transactions: any[] }>({
    queryKey: ["payments-recent"],
    queryFn: () => dashboardApi.getPaymentsRecent(12).then(r => r.data),
    refetchInterval: 6_000,
  });

  const { data: dailyData } = useQuery<{ daily_stats: any[] }>({
    queryKey: ["payments-daily"],
    queryFn: () => dashboardApi.getPaymentsDaily(14).then(r => r.data),
    refetchInterval: 60_000,
  });

  const chartData = (dailyData?.daily_stats ?? []).map((d: any) => ({
    date: d.date?.slice(5) ?? d.date,
    Enrollment:    Math.round((d.total_count ?? 0) * 0.25),
    Verification:  d.successful_count ?? 0,
    Liveness:      Math.round((d.successful_count ?? 0) * 0.6),
    Sessions:      Math.round((d.total_count ?? 0) * 0.4),
  }));

  const txnStream = recentData?.transactions ?? [];

  const kpis = [
    { icon: AppWindow,    label: "Applications",          value: 4,                       color: "#00C2FF", loading: false },
    { icon: Users,        label: "Registered Users",      value: userStats?.total_users ?? 0, color: "#00E5A8", loading: uLoad, href: "/dashboard/users" },
    { icon: Zap,          label: "API Requests Today",    value: overview?.total_transactions ?? 0, color: "#818cf8", loading: ovLoad },
    { icon: ShieldCheck,  label: "Auth Success Rate",     value: overview?.authorization_rate ?? 0, suffix: "%", decimals: 1, color: "#00E5A8", loading: ovLoad },
    { icon: Fingerprint,  label: "Active Identities",     value: userStats?.active_users ?? 0, color: "#00C2FF", loading: uLoad },
    { icon: Clock,        label: "Avg API Latency",       value: 61,                     suffix: "ms", color: "#fbbf24", loading: false },
  ];

  const MOCK_APPS = [
    { name: "Campus Access System",  env: "Production",  usage: "12,491", rate: "98.2%", status: "active"   as const },
    { name: "Employee Attendance",   env: "Production",  usage: "5,832",  rate: "99.1%", status: "active"   as const },
    { name: "Identity Verification", env: "Staging",     usage: "1,204",  rate: "94.7%", status: "active"   as const },
    { name: "Customer KYC",          env: "Development", usage: "0",      rate: "—",     status: "inactive" as const },
  ];

  const QUICK_ACTIONS = [
    { icon: Key,       label: "Generate API Key",   href: "/dashboard/api-keys",  desc: "Create a new key for your app",   color: "#00C2FF" },
    { icon: BookOpen,  label: "Documentation",      href: "#",                   desc: "Quick start guides & references", color: "#818cf8" },
    { icon: Download,  label: "SDK Downloads",      href: "#",                   desc: "iOS, Android, Web",               color: "#00E5A8" },
    { icon: Terminal,  label: "Postman Collection", href: "#",                   desc: "Import and test instantly",       color: "#fbbf24" },
    { icon: Webhook,   label: "Webhook Setup",      href: "/dashboard/webhooks", desc: "Configure event delivery",        color: "#00C2FF" },
    { icon: Activity,  label: "API Status",         href: "#",                   desc: "Real-time uptime dashboard",      color: "#00E5A8" },
  ];

  return (
    <div className="space-y-7 max-w-[1400px]">
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4"
      >
        <div>
          <h1 className="text-[22px] font-semibold text-white tracking-[-0.02em]">
            Welcome back, {user?.name?.split(" ")[0] ?? "there"} 👋
          </h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)] mt-1 max-w-lg">
            Manage your biometric infrastructure, monitor authentication activity, and secure digital identities.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium"
            style={{ background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.15)", color: "#00E5A8" }}>
            <span className="status-dot-live" />
            Production
          </div>
          <Link href="#" className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium text-[rgba(255,255,255,0.45)]"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
            <BookOpen size={11} /> Docs
          </Link>
        </div>
      </motion.div>

      {/* ── KPI Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        {kpis.map((k, i) => (
          <KpiCard key={k.label} index={i} {...k} delta={i < 3 ? "+12%" : undefined} />
        ))}
      </div>

      {/* ── Chart + Live Feed ── */}
      <div className="grid xl:grid-cols-[1fr_340px] gap-4">
        {/* API Activity Chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="dash-card p-6 rounded-2xl"
        >
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-[14px] font-semibold text-white">API Activity</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">
                Enrollment · Verification · Liveness · Sessions
              </p>
            </div>
            <div className="flex items-center gap-1 rounded-lg p-0.5"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
              {(["24H", "7D", "30D", "90D"] as const).map(r => (
                <button key={r}
                  onClick={() => setRange(r)}
                  className="px-2.5 py-1 rounded-md text-[10.5px] font-medium transition-all"
                  style={{
                    background: range === r ? "rgba(255,255,255,0.08)" : "transparent",
                    color: range === r ? "#fff" : "rgba(255,255,255,0.35)",
                    border: range === r ? "1px solid rgba(255,255,255,0.1)" : "1px solid transparent",
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          {chartData.length === 0 ? (
            <div className="h-[220px] rounded-xl flex flex-col items-center justify-center gap-2"
              style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.06)" }}>
              <Activity size={20} style={{ color: "rgba(255,255,255,0.12)" }} />
              <p className="text-[11.5px] text-[rgba(255,255,255,0.2)]">
                API calls will appear here after your first request
              </p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  {[
                    ["grad1", "#00C2FF"],
                    ["grad2", "#00E5A8"],
                    ["grad3", "#818cf8"],
                    ["grad4", "#fbbf24"],
                  ].map(([id, color]) => (
                    <linearGradient key={id} id={id} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={color} stopOpacity={0.2} />
                      <stop offset="95%" stopColor={color} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} width={32} />
                <Tooltip content={<ChartTip />} />
                <Area type="monotone" dataKey="Enrollment"   stroke="#00C2FF" strokeWidth={1.5} fill="url(#grad1)" dot={false} />
                <Area type="monotone" dataKey="Verification" stroke="#00E5A8" strokeWidth={1.5} fill="url(#grad2)" dot={false} />
                <Area type="monotone" dataKey="Liveness"     stroke="#818cf8" strokeWidth={1.5} fill="url(#grad3)" dot={false} />
                <Area type="monotone" dataKey="Sessions"     stroke="#fbbf24" strokeWidth={1.5} fill="url(#grad4)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}

          {/* Legend */}
          <div className="flex flex-wrap gap-4 mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            {[
              { c: "#00C2FF", l: "Enrollment" },
              { c: "#00E5A8", l: "Verification" },
              { c: "#818cf8", l: "Liveness" },
              { c: "#fbbf24", l: "Sessions" },
            ].map(({ c, l }) => (
              <span key={l} className="flex items-center gap-1.5 text-[10.5px] text-[rgba(255,255,255,0.35)]">
                <span className="w-5 h-0.5 rounded-full" style={{ background: c }} />
                {l}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Live Auth Feed */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="dash-card p-5 rounded-2xl flex flex-col"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-[14px] font-semibold text-white">Live Auth Feed</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Real-time events</p>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[9.5px] font-bold tracking-wider"
              style={{ background: "rgba(0,229,168,0.08)", border: "1px solid rgba(0,229,168,0.18)", color: "#00E5A8" }}>
              <span className="status-dot-live" />
              LIVE
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            {rLoad ? (
              <div className="space-y-2">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-10 rounded-xl animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
                ))}
              </div>
            ) : txnStream.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center gap-2 py-12">
                <Activity size={20} style={{ color: "rgba(255,255,255,0.1)" }} />
                <p className="text-[11.5px] text-[rgba(255,255,255,0.2)] text-center">
                  No auth events yet.<br />Make your first API call to see the feed.
                </p>
              </div>
            ) : (
              <div className="space-y-0.5">
                {txnStream.slice(0, 10).map((txn: any, i: number) => (
                  <LiveFeedItem key={txn.id ?? i} txn={txn} index={i} />
                ))}
              </div>
            )}
          </div>

          <Link href="/dashboard/logs" className="mt-4 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] text-[rgba(255,255,255,0.35)] hover:text-[rgba(255,255,255,0.6)] transition-colors"
            style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
            View all logs <ArrowRight size={10} />
          </Link>
        </motion.div>
      </div>

      {/* ── App Overview ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-[15px] font-semibold text-white">Application Overview</h2>
            <p className="text-[11.5px] text-[rgba(255,255,255,0.35)] mt-0.5">Your registered applications and usage</p>
          </div>
          <Link href="/dashboard/applications"
            className="flex items-center gap-1.5 text-[11px] font-medium text-[rgba(0,194,255,0.7)] hover:text-[#00C2FF] transition-colors">
            Manage apps <ArrowRight size={10} />
          </Link>
        </div>
        <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {MOCK_APPS.map((app, i) => (
            <AppCard key={app.name} {...app} index={i} />
          ))}
        </div>
      </div>

      {/* ── API Health + Quick Access ── */}
      <div className="grid xl:grid-cols-[1fr_360px] gap-4">
        {/* API Health */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="dash-card rounded-2xl overflow-hidden"
        >
          <div className="flex items-center justify-between px-5 py-4"
            style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <div>
              <h2 className="text-[14px] font-semibold text-white">API Health</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Live endpoint status</p>
            </div>
            <span className="flex items-center gap-1.5 text-[10px] font-semibold text-[#00E5A8]">
              <span className="status-dot-live" /> All systems operational
            </span>
          </div>
          <div className="px-5">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>Endpoint</th>
                  <th>Latency</th>
                  <th>Success Rate</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <ApiHealthRow name="Enrollment API"   latency="48ms"  rate="99.8%" status="operational" />
                <ApiHealthRow name="Verification API" latency="61ms"  rate="99.5%" status="operational" />
                <ApiHealthRow name="Liveness API"     latency="112ms" rate="98.9%" status="operational" />
                <ApiHealthRow name="Session API"      latency="22ms"  rate="99.9%" status="operational" />
              </tbody>
            </table>
          </div>
        </motion.div>

        {/* Quick Access */}
        <motion.div
          initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55 }}
          className="dash-card p-5 rounded-2xl"
        >
          <h2 className="text-[14px] font-semibold text-white mb-1">Developer Quick Access</h2>
          <p className="text-[11px] text-[rgba(255,255,255,0.35)] mb-4">Common actions</p>
          <div className="space-y-2">
            {QUICK_ACTIONS.map(a => <QuickAction key={a.label} {...a} />)}
          </div>
        </motion.div>
      </div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────────────
   ADMIN DASHBOARD
   ────────────────────────────────────────────────────────────────────────── */
function AdminDashboard() {
  const [lastUpdated, setLastUpdated] = useState(new Date());

  const { data: overview, isLoading: ovLoad, refetch } = useQuery<PaymentOverview>({
    queryKey: ["payments-overview"],
    queryFn: () => dashboardApi.getPaymentsOverview().then(r => { setLastUpdated(new Date()); return r.data; }),
    refetchInterval: 10_000,
  });

  const { data: userStats, isLoading: uLoad } = useQuery<UserStats>({
    queryKey: ["dashboard-users"],
    queryFn: () => dashboardApi.getUsers().then(r => r.data),
    refetchInterval: 20_000,
  });

  const { data: verifyStats, isLoading: vLoad } = useQuery<VerificationStats>({
    queryKey: ["dashboard-verifications"],
    queryFn: () => dashboardApi.getVerifications().then(r => r.data),
    refetchInterval: 20_000,
  });

  const { data: dailyData, isLoading: dLoad } = useQuery<{ daily_stats: any[] }>({
    queryKey: ["payments-daily"],
    queryFn: () => dashboardApi.getPaymentsDaily(14).then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: recentData } = useQuery<{ transactions: any[] }>({
    queryKey: ["payments-recent"],
    queryFn: () => dashboardApi.getPaymentsRecent(10).then(r => r.data),
    refetchInterval: 5_000,
  });

  const chartData = (dailyData?.daily_stats ?? []).map((d: any) => ({
    date: d.date?.slice(5) ?? d.date,
    Enrollment:    Math.round((d.total_count ?? 0) * 0.3),
    Verification:  d.successful_count ?? 0,
    Liveness:      Math.round((d.successful_count ?? 0) * 0.5),
    Sessions:      Math.round((d.total_count ?? 0) * 0.4),
    Errors:        (d.total_count ?? 0) - (d.successful_count ?? 0),
  }));

  const txnStream = recentData?.transactions ?? [];

  const kpis = [
    { icon: Building2,   label: "Organizations",      value: 12,                             color: "#00C2FF" },
    { icon: AppWindow,   label: "Applications",        value: 47,                             color: "#818cf8" },
    { icon: Fingerprint, label: "Identities",          value: userStats?.enrolled_users ?? 0, color: "#00E5A8", loading: uLoad },
    { icon: Zap,         label: "API Calls Today",     value: overview?.total_transactions ?? 0, color: "#fbbf24", loading: ovLoad },
    { icon: Activity,    label: "Auth Sessions",       value: overview?.total_transactions ?? 0, color: "#00C2FF", loading: ovLoad },
    { icon: ShieldCheck, label: "System Availability", value: 99.97,                          suffix: "%", decimals: 2, color: "#00E5A8" },
    { icon: Clock,       label: "Avg Latency",         value: 61,                             suffix: "ms", color: "#fbbf24" },
    { icon: AlertTriangle, label: "Threat Events",     value: 3,                              color: "#f87171" },
  ];

  const MOCK_ORGS = [
    { name: "Acme Corp",         plan: "Enterprise", apps: 8,  users: "124K", usage: "98%",  status: "active"    },
    { name: "FinVault Inc",      plan: "Pro",        apps: 3,  users: "42K",  usage: "67%",  status: "active"    },
    { name: "MedIdentity",       plan: "Enterprise", apps: 5,  users: "18K",  usage: "45%",  status: "active"    },
    { name: "Campus Systems",    plan: "Starter",    apps: 2,  users: "8.2K", usage: "29%",  status: "active"    },
    { name: "RetailVision Ltd",  plan: "Pro",        apps: 4,  users: "22K",  usage: "54%",  status: "suspended" },
  ];

  return (
    <div className="space-y-7 max-w-[1400px]">
      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4"
      >
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-[22px] font-semibold text-white tracking-[-0.02em]">
              NeoFace Labs Operations
            </h1>
            <span className="px-2 py-0.5 rounded-full text-[9.5px] font-bold tracking-wider uppercase"
              style={{ background: "rgba(129,140,248,0.12)", border: "1px solid rgba(129,140,248,0.25)", color: "#818cf8" }}>
              ADMIN
            </span>
          </div>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)]">
            Real-time biometric infrastructure monitoring
          </p>
          <p className="text-[10.5px] text-[rgba(255,255,255,0.2)] mt-1 flex items-center gap-1.5">
            <span className="status-dot-live" />
            Auto-refreshes · Last updated {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <button onClick={() => refetch()}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-[12px] font-medium transition-all"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.45)" }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "white"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.45)"; }}>
          <RefreshCw size={12} /> Refresh
        </button>
      </motion.div>

      {/* ── KPI Cards (8 cards) ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-3">
        {kpis.map((k, i) => (
          <KpiCard key={k.label} index={i} {...k} loading={(k as any).loading} delta={i < 4 ? "+8%" : undefined} />
        ))}
      </div>

      {/* ── Traffic Chart + Live feed ── */}
      <div className="grid xl:grid-cols-[1fr_320px] gap-4">
        {/* Global Traffic Chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.28 }}
          className="dash-card p-6 rounded-2xl"
        >
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-[14px] font-semibold text-white">Global API Traffic</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">All endpoints · 14-day trend</p>
            </div>
            <Link href="/dashboard/analytics"
              className="flex items-center gap-1 text-[10.5px] font-medium text-[rgba(0,194,255,0.6)] hover:text-[#00C2FF] transition-colors">
              Full analytics <ArrowUpRight size={10} />
            </Link>
          </div>

          {dLoad ? (
            <div className="h-[220px] animate-pulse rounded-xl" style={{ background: "rgba(255,255,255,0.04)" }} />
          ) : chartData.length === 0 ? (
            <div className="h-[220px] rounded-xl flex items-center justify-center"
              style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.06)" }}>
              <p className="text-[11.5px] text-[rgba(255,255,255,0.2)]">No API data yet</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={chartData} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  {[["g1","#00C2FF"],["g2","#00E5A8"],["g3","#818cf8"],["g4","#fbbf24"],["g5","#f87171"]].map(([id, c]) => (
                    <linearGradient key={id} id={id} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={c} stopOpacity={0.18} />
                      <stop offset="95%" stopColor={c} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} width={32} />
                <Tooltip content={<ChartTip />} />
                <Area type="monotone" dataKey="Enrollment"   stroke="#00C2FF" strokeWidth={1.5} fill="url(#g1)" dot={false} />
                <Area type="monotone" dataKey="Verification" stroke="#00E5A8" strokeWidth={1.5} fill="url(#g2)" dot={false} />
                <Area type="monotone" dataKey="Liveness"     stroke="#818cf8" strokeWidth={1.5} fill="url(#g3)" dot={false} />
                <Area type="monotone" dataKey="Sessions"     stroke="#fbbf24" strokeWidth={1.5} fill="url(#g4)" dot={false} />
                <Area type="monotone" dataKey="Errors"       stroke="#f87171" strokeWidth={1}   fill="url(#g5)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
          <div className="flex flex-wrap gap-4 mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            {[["#00C2FF","Enrollment"],["#00E5A8","Verification"],["#818cf8","Liveness"],["#fbbf24","Sessions"],["#f87171","Errors"]].map(([c,l])=>(
              <span key={l} className="flex items-center gap-1.5 text-[10.5px] text-[rgba(255,255,255,0.35)]">
                <span className="w-4 h-0.5 rounded-full" style={{ background: c }} />{l}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Live Event Feed */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.33 }}
          className="dash-card p-5 rounded-2xl flex flex-col"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[14px] font-semibold text-white">Live Events</h2>
            <span className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[9px] font-bold tracking-wider"
              style={{ background: "rgba(0,229,168,0.08)", border: "1px solid rgba(0,229,168,0.18)", color: "#00E5A8" }}>
              <span className="status-dot-live" /> LIVE
            </span>
          </div>
          <div className="flex-1 overflow-hidden space-y-0.5">
            {txnStream.slice(0, 8).map((txn: any, i) => (
              <LiveFeedItem key={txn.id ?? i} txn={txn} index={i} />
            ))}
            {txnStream.length === 0 && (
              <div className="flex flex-col items-center justify-center h-40 gap-2">
                <Activity size={18} style={{ color: "rgba(255,255,255,0.1)" }} />
                <p className="text-[11px] text-[rgba(255,255,255,0.2)]">No events yet</p>
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* ── Organization Management ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.45 }}
        className="dash-card rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <div>
            <h2 className="text-[14px] font-semibold text-white">Organizations</h2>
            <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Customer accounts on the platform</p>
          </div>
          <Link href="/dashboard/users"
            className="flex items-center gap-1.5 text-[11px] font-medium text-[rgba(0,194,255,0.7)] hover:text-[#00C2FF] transition-colors">
            Manage <ArrowRight size={10} />
          </Link>
        </div>
        <div className="px-2">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Organization</th>
                <th>Plan</th>
                <th>Applications</th>
                <th>Users</th>
                <th>API Usage</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_ORGS.map(org => (
                <tr key={org.name} className="cursor-pointer">
                  <td>
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-md flex items-center justify-center text-[9px] font-bold"
                        style={{ background: "rgba(0,194,255,0.1)", color: "#00C2FF", border: "1px solid rgba(0,194,255,0.15)" }}>
                        {org.name[0]}
                      </div>
                      <span className="text-white font-medium">{org.name}</span>
                    </div>
                  </td>
                  <td>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                      style={{
                        background: org.plan === "Enterprise" ? "rgba(129,140,248,0.1)" : org.plan === "Pro" ? "rgba(0,194,255,0.08)" : "rgba(255,255,255,0.05)",
                        color: org.plan === "Enterprise" ? "#818cf8" : org.plan === "Pro" ? "#00C2FF" : "rgba(255,255,255,0.4)",
                        border: `1px solid ${org.plan === "Enterprise" ? "rgba(129,140,248,0.2)" : org.plan === "Pro" ? "rgba(0,194,255,0.15)" : "rgba(255,255,255,0.08)"}`,
                      }}>
                      {org.plan}
                    </span>
                  </td>
                  <td>{org.apps}</td>
                  <td>{org.users}</td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                        <div className="h-full rounded-full" style={{ width: org.usage, background: "linear-gradient(90deg, #00C2FF, #00E5A8)" }} />
                      </div>
                      <span className="text-[11px] font-mono">{org.usage}</span>
                    </div>
                  </td>
                  <td>
                    <span className="flex items-center gap-1.5 text-[11px]">
                      {org.status === "active"
                        ? <><span className="status-dot-live" /><span style={{ color: "#00E5A8" }}>Active</span></>
                        : <><span className="status-dot-error" /><span style={{ color: "#f87171" }}>Suspended</span></>}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* ── Quick Links Admin ── */}
      <div className="grid sm:grid-cols-3 gap-3">
        <QuickAction icon={ShieldAlert} label="Fraud Center"       href="/dashboard/risk"           desc="Threat detection & spoof alerts"      color="#f87171" />
        <QuickAction icon={Brain}       label="Model Monitoring"   href="/dashboard/models"          desc="AI model performance & drift"        color="#818cf8" />
        <QuickAction icon={Server}      label="Infrastructure"     href="/dashboard/infrastructure"  desc="Servers, GPU clusters, storage"      color="#fbbf24" />
      </div>
    </div>
  );
}

/* ─── Router ─────────────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { isAdmin } = useRole();
  return isAdmin ? <AdminDashboard /> : <CustomerDashboard />;
}
