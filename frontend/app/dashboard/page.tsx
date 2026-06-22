"use client";
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  DollarSign, ShieldCheck, TrendingUp, Fingerprint,
  RefreshCw, Eye, Scan, ArrowUpRight, Zap, Lock, CheckCircle2, XCircle, AlertCircle,
  UserCircle, Shield, Brain, CreditCard, History, ArrowRight, Crown,
} from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { dashboardApi, trustEngineApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import type { PaymentOverview, UserStats, VerificationStats } from "@/types";
import { useRole } from "@/hooks/use-role";
import { useAuthStore } from "@/store/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";

/* ── Animated counter ────────────────────────────────────────────────────── */
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
      const p = Math.min((now - start) / 1200, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(target * ease);
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target]);
  return (
    <>
      {prefix}
      {decimals === 0 ? Math.round(val).toLocaleString() : val.toFixed(decimals)}
      {suffix}
    </>
  );
}

/* ── Metric card ─────────────────────────────────────────────────────────── */
function MetricCard({ icon: Icon, label, value, prefix, suffix, decimals, delta, accentColor, glowColor, loading, index, href }: {
  icon: any; label: string; value: number; prefix?: string; suffix?: string;
  decimals?: number; delta?: string; accentColor: string; glowColor: string;
  loading?: boolean; index: number; href?: string;
}) {
  const router = useRouter();
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.08, ease: [0.16, 1, 0.3, 1] }}
      whileHover={href ? { y: -2, scale: 1.015, transition: { duration: 0.2 } } : { y: -2, transition: { duration: 0.2 } }}
      onClick={() => href && router.push(href)}
      className={`relative rounded-2xl overflow-hidden group ${href ? "cursor-pointer" : "cursor-default"}`}
      style={{ background: "rgba(255,255,255,0.025)", border: `1px solid rgba(255,255,255,0.07)`, boxShadow: "0 1px 24px rgba(0,0,0,0.4)" }}
    >
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none rounded-2xl"
        style={{ boxShadow: `inset 0 0 40px ${glowColor}08`, border: `1px solid ${glowColor}20` }} />
      <div className="absolute top-0 left-6 right-6 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${accentColor}40, transparent)` }} />
      <div className="p-5">
        <div className="flex items-start justify-between mb-4">
          <p className="text-[11.5px] text-[rgba(255,255,255,0.35)] font-medium uppercase tracking-wider">{label}</p>
          <div className="w-8 h-8 rounded-xl flex items-center justify-center"
            style={{ background: `${glowColor}12`, border: `1px solid ${glowColor}20`, boxShadow: `0 0 12px ${glowColor}15` }}>
            <Icon size={14} style={{ color: accentColor }} />
          </div>
        </div>
        {loading ? (
          <div className="h-9 w-28 rounded-lg animate-pulse" style={{ background: "rgba(255,255,255,0.06)" }} />
        ) : (
          <p className="text-[32px] font-bold leading-none tracking-tight" style={{ color: accentColor }}>
            <Counter target={value} prefix={prefix} suffix={suffix} decimals={decimals} />
          </p>
        )}
        {delta && (
          <p className="text-[11px] mt-2 flex items-center gap-1" style={{ color: "rgba(255,255,255,0.28)" }}>
            <ArrowUpRight size={11} style={{ color: "#00E5A8" }} />
            <span style={{ color: "#00E5A8" }}>{delta}</span>
            <span>vs last period</span>
          </p>
        )}
      </div>
    </motion.div>
  );
}

/* ── Chart tooltip ───────────────────────────────────────────────────────── */
function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl p-3 text-[11px] shadow-2xl"
      style={{ background: "rgba(5,5,5,0.95)", border: "1px solid rgba(0,194,255,0.15)", backdropFilter: "blur(12px)" }}>
      <p className="text-[rgba(255,255,255,0.4)] mb-2 font-medium">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center gap-2 mb-1">
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: p.color }} />
          <span style={{ color: "rgba(255,255,255,0.5)" }}>{p.name}:</span>
          <strong style={{ color: p.color }}>
            {p.dataKey === "volume" ? `$${Number(p.value).toLocaleString()}` : p.value.toLocaleString()}
          </strong>
        </p>
      ))}
    </div>
  );
}

/* ── Modality badge ──────────────────────────────────────────────────────── */
function ModalityBadge({ modality }: { modality: string }) {
  const map: Record<string, { icon: any; color: string; label: string }> = {
    face:        { icon: Scan,        color: "#00E5A8", label: "Face" },
    iris:        { icon: Eye,         color: "#00C2FF", label: "Iris (Coming Soon Q4 2026)" },
    fingerprint: { icon: Fingerprint, color: "#818cf8", label: "Print" },
    multi_modal: { icon: ShieldCheck, color: "#f59e0b", label: "Multi" },
  };
  const m = map[modality] ?? map["face"];
  return (
    <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[9px] font-semibold shrink-0"
      style={{ background: `${m.color}12`, border: `1px solid ${m.color}25`, color: m.color }}>
      <m.icon size={9} />
      {m.label}
    </div>
  );
}

/* ── User Personal Dashboard (non-admin) ─────────────────────────────────── */
function UserDashboard() {
  const user = useAuthStore((s) => s.user);

  const { data: enrollmentStatus } = useQuery({
    queryKey: ["trust-engine-enrollment"],
    queryFn: () => trustEngineApi.getEnrollmentStatus().then(r => r.data),
    retry: 1,
  });

  const { data: recentData } = useQuery<{ transactions: any[] }>({
    queryKey: ["payments-recent-user"],
    queryFn: () => dashboardApi.getPaymentsRecent(5).then(r => r.data),
    refetchInterval: 10_000,
  });

  const quickLinks = [
    { href: "/dashboard/trust-engine", icon: Shield,      label: "Trust Engine",    desc: "Run your biometric scan",     color: "#818cf8" },
    { href: "/dashboard/identity",     icon: UserCircle,  label: "My Identity",     desc: "Manage face enrollment",       color: "#00E5A8" },
    { href: "/dashboard/bank-accounts",icon: CreditCard,  label: "Payment Methods", desc: "Manage linked accounts",       color: "#00C2FF" },
    { href: "/dashboard/logs",         icon: History,     label: "My Transactions", desc: "View your activity log",       color: "#f59e0b" },
    { href: "/dashboard/fingerprint",  icon: Fingerprint, label: "Fingerprint Auth",desc: "Set up WebAuthn passkey",      color: "#f87171" },
    { href: "/dashboard/behavioral",   icon: Brain,       label: "Behavior Profile",desc: "View your behavior baseline",  color: "#a78bfa" },
  ];

  const txns = recentData?.transactions ?? [];

  return (
    <div className="space-y-7">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="text-[22px] font-bold text-white tracking-tight">
          Welcome back, {user?.name?.split(" ")[0] ?? "there"} 👋
        </h1>
        <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
          Your personal NeoFace dashboard — all data shown is yours only
        </p>
      </motion.div>

      {/* Enrollment Status Banner */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="rounded-2xl p-5 flex items-center gap-5"
        style={{
          background: enrollmentStatus?.face_enrolled
            ? "linear-gradient(135deg, rgba(0,229,168,0.06), rgba(0,194,255,0.04))"
            : "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(0,194,255,0.04))",
          border: enrollmentStatus?.face_enrolled
            ? "1px solid rgba(0,229,168,0.2)"
            : "1px solid rgba(99,102,241,0.25)",
        }}
      >
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0"
          style={{
            background: enrollmentStatus?.face_enrolled ? "rgba(0,229,168,0.12)" : "rgba(99,102,241,0.12)",
            border: enrollmentStatus?.face_enrolled ? "1px solid rgba(0,229,168,0.25)" : "1px solid rgba(99,102,241,0.25)",
          }}>
          {enrollmentStatus?.face_enrolled
            ? <ShieldCheck size={24} style={{ color: "#00E5A8" }} />
            : <UserCircle size={24} style={{ color: "#818cf8" }} />
          }
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[14px] font-bold text-white">
            {enrollmentStatus?.face_enrolled ? "Identity Verified & Enrolled" : "Complete Your Biometric Enrollment"}
          </p>
          <p className="text-[12px] text-[rgba(255,255,255,0.35)] mt-0.5">
            {enrollmentStatus?.face_enrolled
              ? `${enrollmentStatus.face_embedding_count} face angle${enrollmentStatus.face_embedding_count !== 1 ? "s" : ""} enrolled · Ready for Trust Engine verification`
              : "Enroll your face to unlock the Trust Engine and biometric payments"}
          </p>
        </div>
        <Link
          href={enrollmentStatus?.face_enrolled ? "/dashboard/trust-engine" : "/dashboard/identity"}
          className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-xl text-[12px] font-semibold transition-all"
          style={{
            background: enrollmentStatus?.face_enrolled ? "rgba(0,229,168,0.12)" : "rgba(99,102,241,0.15)",
            border: enrollmentStatus?.face_enrolled ? "1px solid rgba(0,229,168,0.3)" : "1px solid rgba(99,102,241,0.35)",
            color: enrollmentStatus?.face_enrolled ? "#00E5A8" : "#818cf8",
          }}
        >
          {enrollmentStatus?.face_enrolled ? "Run Scan" : "Enroll Now"}
          <ArrowRight size={13} />
        </Link>
      </motion.div>

      {/* Quick Links */}
      <div>
        <p className="text-[11px] font-semibold text-[rgba(255,255,255,0.25)] uppercase tracking-wider mb-3">Quick Access</p>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {quickLinks.map(({ href, icon: Icon, label, desc, color }, i) => (
            <motion.div
              key={href}
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 + i * 0.05 }}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
            >
              <Link href={href} className="block rounded-2xl p-4 group transition-all"
                style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.07)" }}
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center mb-3"
                  style={{ background: `${color}12`, border: `1px solid ${color}25` }}>
                  <Icon size={16} style={{ color }} />
                </div>
                <p className="text-[13px] font-semibold text-white group-hover:text-[rgba(255,255,255,0.9)] mb-0.5">{label}</p>
                <p className="text-[10.5px] text-[rgba(255,255,255,0.3)]">{desc}</p>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
        className="rounded-2xl p-5"
        style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)" }}
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-[14px] font-semibold text-white">Recent Activity</h2>
            <p className="text-[11px] text-[rgba(255,255,255,0.28)] mt-0.5">Your last 5 transactions</p>
          </div>
          <Link href="/dashboard/logs" className="text-[11px] text-[rgba(0,194,255,0.6)] hover:text-[#00C2FF] transition-colors flex items-center gap-1">
            View all <ArrowRight size={10} />
          </Link>
        </div>
        {txns.length === 0 ? (
          <div className="py-8 flex flex-col items-center gap-2">
            <AlertCircle size={20} style={{ color: "rgba(255,255,255,0.1)" }} />
            <p className="text-[12px] text-[rgba(255,255,255,0.2)]">No transactions yet — use the Checkout Demo to test</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {txns.map((txn: any, i: number) => (
              <motion.div key={txn.id ?? i}
                initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.45 + i * 0.04 }}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-[rgba(255,255,255,0.03)] transition-all"
              >
                <div className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: txn.authentication_result ? "rgba(0,229,168,0.12)" : "rgba(248,113,113,0.12)" }}>
                  {txn.authentication_result
                    ? <CheckCircle2 size={12} style={{ color: "#00E5A8" }} />
                    : <XCircle size={12} style={{ color: "#f87171" }} />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] font-medium text-[rgba(255,255,255,0.7)] truncate">
                    {txn.authentication_result ? "Payment Authorized" : (txn.failure_reason ?? "Payment Failed")}
                  </p>
                  <p className="text-[10px] text-[rgba(255,255,255,0.25)]">{txn.created_at ? formatDate(txn.created_at) : "—"}</p>
                </div>
                <span className="text-[13px] font-bold shrink-0"
                  style={{ color: txn.authentication_result ? "#00E5A8" : "rgba(248,113,113,0.7)" }}>
                  {txn.authentication_result ? "+" : "-"}${Number(txn.amount ?? 0).toFixed(2)}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}

/* ── Main dashboard ──────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { isAdmin } = useRole();

  // Regular users get their personal dashboard
  if (!isAdmin) return <UserDashboard />;

  // ── ADMIN: Global Command Center below ──────────────────────────────────────
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const { data: overview, isLoading: ovLoad, refetch } = useQuery<PaymentOverview>({
    queryKey: ["payments-overview"],
    queryFn: () => dashboardApi.getPaymentsOverview().then(r => { setLastUpdated(new Date()); return r.data; }),
    refetchInterval: 10_000, // 10s live
  });

  const { data: dailyData, isLoading: dLoad } = useQuery<{ daily_stats: any[] }>({
    queryKey: ["payments-daily"],
    queryFn: () => dashboardApi.getPaymentsDaily(14).then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: recentData, isLoading: rLoad } = useQuery<{ transactions: any[] }>({
    queryKey: ["payments-recent"],
    queryFn: () => dashboardApi.getPaymentsRecent(10).then(r => r.data),
    refetchInterval: 5_000,  // 5s for live transaction feed
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

  const chartData = (dailyData?.daily_stats ?? []).map((d: any) => ({
    date: d.date?.slice(5) ?? d.date,
    authorized: d.successful_count ?? d.successful ?? 0,
    blocked: (d.total_count ?? d.total ?? 0) - (d.successful_count ?? d.successful ?? 0),
    volume: Math.round(d.volume ?? 0),
  }));

  const txnStream = recentData?.transactions ?? [];

  return (
    <div className="space-y-7">
      {/* ── Header ──────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }} className="flex items-start justify-between"
      >
        <div>
          <h1 className="text-[22px] font-bold text-white tracking-tight">Command Center</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
            Biometric payment authorization — live transaction feed
          </p>
          <p className="text-[10px] text-[rgba(255,255,255,0.2)] mt-1 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ background: "#00E5A8", boxShadow: "0 0 4px #00E5A8", animation: "pulse 1.5s infinite" }} />
            Auto-refreshes every 10s · Last updated {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-[12px] font-medium transition-all"
          style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.4)" }}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = "white"; (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(0,194,255,0.25)"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.4)"; (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.08)"; }}
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </motion.div>

      {/* ── Metric Cards ─────────────────────────────────────── */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        <MetricCard
          index={0} icon={DollarSign} label="Total Volume"
          value={overview?.total_volume_usd ?? 0} prefix="$" decimals={0}
          accentColor="#00C2FF" glowColor="#00C2FF" loading={ovLoad}
          href="/dashboard/logs"
        />
        <MetricCard
          index={1} icon={ShieldCheck} label="Transactions"
          value={overview?.total_transactions ?? 0}
          accentColor="#00E5A8" glowColor="#00E5A8" loading={ovLoad}
          href="/dashboard/logs"
        />
        <MetricCard
          index={2} icon={TrendingUp} label="Authorization Rate"
          value={overview?.authorization_rate ?? 0} suffix="%" decimals={1}
          accentColor="#818cf8" glowColor="#818cf8" loading={ovLoad}
          href="/dashboard/risk"
        />
        <MetricCard
          index={3} icon={Fingerprint} label="Active Identities"
          value={userStats?.active_users ?? 0}
          accentColor="#f59e0b" glowColor="#f59e0b" loading={uLoad}
          href="/dashboard/users"
        />
      </div>

      {/* ── Chart + Live Stream ───────────────────────────────── */}
      <div className="grid xl:grid-cols-3 gap-4">
        {/* Chart */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="xl:col-span-2 rounded-2xl p-5 relative overflow-hidden"
          style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)", boxShadow: "0 1px 30px rgba(0,0,0,0.4)" }}
        >
          <div className="absolute top-0 left-1/4 right-1/4 h-px pointer-events-none"
            style={{ background: "linear-gradient(90deg, transparent, rgba(0,194,255,0.4), transparent)" }} />

          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-[14px] font-semibold text-white">Payment Authorization Flow</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.28)] mt-0.5">Authorized vs. Blocked — last 14 days</p>
            </div>
            <div className="flex items-center gap-4 text-[10.5px]" style={{ color: "rgba(255,255,255,0.28)" }}>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ background: "#00C2FF" }} />Authorized</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ background: "#f87171" }} />Blocked</span>
            </div>
          </div>

          {dLoad ? (
            <div className="h-48 rounded-xl animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
          ) : chartData.length === 0 ? (
            <div className="h-48 rounded-xl flex flex-col items-center justify-center gap-2"
              style={{ background: "rgba(255,255,255,0.02)", border: "1px dashed rgba(255,255,255,0.08)" }}>
              <AlertCircle size={20} style={{ color: "rgba(255,255,255,0.15)" }} />
              <p className="text-[12px] text-[rgba(255,255,255,0.2)]">No transaction data yet. Authorize a payment to see the chart.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={210}>
              <AreaChart data={chartData} margin={{ top: 4, right: 0, left: -24, bottom: 0 }}>
                <defs>
                  <linearGradient id="gAuth" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00C2FF" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#00C2FF" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gBlk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#f87171" stopOpacity={0.18} />
                    <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.2)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.2)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="authorized" name="Authorized" stroke="#00C2FF" strokeWidth={2} fill="url(#gAuth)" dot={false} />
                <Area type="monotone" dataKey="blocked"    name="Blocked"    stroke="#f87171" strokeWidth={1.5} fill="url(#gBlk)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Live Payment Stream */}
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="rounded-2xl p-5 flex flex-col"
          style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)", boxShadow: "0 1px 30px rgba(0,0,0,0.4)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-[14px] font-semibold text-white">Live Transactions</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.28)] mt-0.5">Real payment stream</p>
            </div>
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[9.5px] font-semibold"
              style={{ background: "rgba(0,229,168,0.08)", border: "1px solid rgba(0,229,168,0.2)", color: "#00E5A8" }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#00E5A8", boxShadow: "0 0 4px #00E5A8", animation: "pulse 1.5s infinite" }} />
              LIVE
            </div>
          </div>

          <div className="flex-1 overflow-hidden">
            {rLoad ? (
              <div className="space-y-2.5">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="h-11 rounded-xl animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
                ))}
              </div>
            ) : txnStream.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center gap-2 py-8">
                <AlertCircle size={18} style={{ color: "rgba(255,255,255,0.12)" }} />
                <p className="text-[11px] text-center text-[rgba(255,255,255,0.2)]">
                  No transactions yet.<br />Use the Checkout Demo to authorize a payment.
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {txnStream.slice(0, 9).map((txn: any, i: number) => (
                  <motion.div
                    key={txn.id ?? i}
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.35 + i * 0.04, duration: 0.3 }}
                    className="group flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all duration-200"
                    style={{ background: "rgba(255,255,255,0)" }}
                    onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.03)")}
                    onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,0)")}
                  >
                    <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                      style={{ background: txn.authentication_result ? "rgba(0,229,168,0.12)" : "rgba(248,113,113,0.12)" }}>
                      {txn.authentication_result
                        ? <CheckCircle2 size={10} style={{ color: "#00E5A8" }} />
                        : <XCircle size={10} style={{ color: "#f87171" }} />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="text-[11.5px] text-[rgba(255,255,255,0.75)] font-medium truncate">
                          {txn.authentication_result ? "Authorized" : (txn.failure_reason ?? "Blocked")}
                        </p>
                        <ModalityBadge modality={txn.modality ?? "face"} />
                      </div>
                      <p className="text-[9.5px] text-[rgba(255,255,255,0.22)] mt-0.5">
                        {txn.created_at ? formatDate(txn.created_at) : "—"}
                      </p>
                    </div>
                    <span className="text-[12px] font-semibold shrink-0"
                      style={{ color: txn.authentication_result ? "#00E5A8" : "rgba(248,113,113,0.7)" }}>
                      {txn.authentication_result ? "+" : ""}${Number(txn.amount ?? 0).toFixed(2)}
                    </span>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* ── Modality Breakdown + Summary ─────────────────────── */}
      <div className="grid md:grid-cols-3 gap-3">
        {[
          {
            label: "Enrollment Coverage",
            value: userStats?.enrollment_rate ?? 0,
            suffix: "%",
            color: "#00C2FF",
            glow: "rgba(0,194,255,0.05)",
            icon: Lock,
            desc: "of users biometrically enrolled",
            loading: uLoad,
          },
          {
            label: "Auth Success Rate",
            value: verifyStats?.success_rate ?? (overview?.authorization_rate ?? 0),
            suffix: "%",
            color: "#00E5A8",
            glow: "rgba(0,229,168,0.05)",
            icon: ShieldCheck,
            desc: "biometric authorizations passed",
            loading: vLoad || ovLoad,
          },
          {
            label: "Enrolled Identities",
            value: userStats?.enrolled_users ?? 0,
            suffix: "",
            color: "#818cf8",
            glow: "rgba(129,140,248,0.05)",
            icon: Fingerprint,
            desc: "identity profiles active",
            loading: uLoad,
          },
        ].map((item, i) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45 + i * 0.07 }}
            whileHover={{ y: -2, transition: { duration: 0.2 } }}
            className="rounded-2xl p-5 relative overflow-hidden group cursor-default"
            style={{ background: item.glow, border: "1px solid rgba(255,255,255,0.07)", boxShadow: "0 1px 24px rgba(0,0,0,0.4)" }}
          >
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
              style={{ boxShadow: `inset 0 0 30px ${item.color}08` }} />
            <div className="flex items-start justify-between mb-3">
              <p className="text-[11px] text-[rgba(255,255,255,0.35)] font-medium uppercase tracking-wider">{item.label}</p>
              <item.icon size={13} style={{ color: item.color, opacity: 0.7 }} />
            </div>
            {item.loading ? (
              <div className="h-8 w-24 rounded-lg animate-pulse" style={{ background: "rgba(255,255,255,0.06)" }} />
            ) : (
              <p className="text-[28px] font-bold leading-none" style={{ color: item.color }}>
                <Counter target={item.value} suffix={item.suffix} decimals={item.suffix === "%" ? 1 : 0} />
              </p>
            )}
            <p className="text-[10.5px] text-[rgba(255,255,255,0.22)] mt-2">{item.desc}</p>
          </motion.div>
        ))}
      </div>

      {/* ── Modality Breakdown Pill Row ───────────────────────── */}
      {overview?.modality_breakdown && Object.keys(overview.modality_breakdown).length > 0 && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}
          className="rounded-2xl p-4"
          style={{ background: "rgba(255,255,255,0.015)", border: "1px solid rgba(255,255,255,0.06)" }}
        >
          <p className="text-[11px] text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-3 font-medium">Biometric Modality Breakdown</p>
          <div className="flex flex-wrap gap-3">
            {Object.entries(overview.modality_breakdown).map(([mod, count]) => {
              const colors: Record<string, string> = { face: "#00E5A8", iris: "#00C2FF", fingerprint: "#818cf8", multi_modal: "#f59e0b" };
              const color = colors[mod] ?? "#ffffff";
              return (
                <div key={mod} className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-[11px] font-medium"
                  style={{ background: `${color}10`, border: `1px solid ${color}20`, color }}>
                  <span className="font-bold">{count as number}</span>
                  <span className="opacity-60">{mod.replace("_", " ")}</span>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}
    </div>
  );
}
