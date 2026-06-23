"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3, Globe, Smartphone, TrendingUp, Users, Activity, ShieldCheck, Zap,
  ArrowUpRight, RefreshCw,
} from "lucide-react";
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid,
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
} from "recharts";
import { dashboardApi } from "@/lib/api";
import type { PaymentOverview, UserStats, VerificationStats } from "@/types";

function ChartTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl px-3 py-2.5 text-[11px] shadow-xl"
      style={{ background: "rgba(8,8,8,0.96)", border: "1px solid rgba(255,255,255,0.1)", backdropFilter: "blur(12px)" }}>
      <p className="text-[rgba(255,255,255,0.4)] mb-2 text-[10px]">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center gap-2 mb-0.5">
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: p.color }} />
          <span className="text-[rgba(255,255,255,0.45)]">{p.name}:</span>
          <strong style={{ color: p.color }}>{Number(p.value).toLocaleString()}</strong>
        </p>
      ))}
    </div>
  );
}

const TIME_RANGES = ["24H", "7D", "30D", "90D"] as const;

const GEO_DATA = [
  { country: "India",         requests: 42100, color: "#00E5A8" },
  { country: "United States", requests: 31800, color: "#00C2FF" },
  { country: "Germany",       requests: 18400, color: "#818cf8" },
  { country: "Brazil",        requests: 12300, color: "#fbbf24" },
  { country: "Singapore",     requests: 9600,  color: "#f87171" },
  { country: "Others",        requests: 11200, color: "rgba(255,255,255,0.2)" },
];

const DEVICE_DATA = [
  { name: "Android", value: 48, color: "#00E5A8" },
  { name: "iOS",     value: 35, color: "#00C2FF" },
  { name: "Web",     value: 14, color: "#818cf8" },
  { name: "Other",   value: 3,  color: "rgba(255,255,255,0.2)" },
];

function RangeSelector({ range, setRange }: {
  range: string;
  setRange: (r: typeof TIME_RANGES[number]) => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-lg p-0.5"
      style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
      {TIME_RANGES.map(r => (
        <button key={r} onClick={() => setRange(r)}
          className="px-2.5 py-1 rounded-md text-[10.5px] font-medium transition-all"
          style={{
            background: range === r ? "rgba(255,255,255,0.08)" : "transparent",
            color: range === r ? "#fff" : "rgba(255,255,255,0.35)",
            border: range === r ? "1px solid rgba(255,255,255,0.1)" : "1px solid transparent",
          }}>
          {r}
        </button>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const [range, setRange] = useState<typeof TIME_RANGES[number]>("7D");

  const { data: overview } = useQuery<PaymentOverview>({
    queryKey: ["payments-overview"],
    queryFn: () => dashboardApi.getPaymentsOverview().then(r => r.data),
    refetchInterval: 20_000,
  });

  const { data: dailyData, isLoading } = useQuery<{ daily_stats: any[] }>({
    queryKey: ["payments-daily"],
    queryFn: () => dashboardApi.getPaymentsDaily(14).then(r => r.data),
    refetchInterval: 60_000,
  });

  const { data: userStats } = useQuery<UserStats>({
    queryKey: ["dashboard-users"],
    queryFn: () => dashboardApi.getUsers().then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: verifyStats } = useQuery<VerificationStats>({
    queryKey: ["dashboard-verifications"],
    queryFn: () => dashboardApi.getVerifications().then(r => r.data),
    refetchInterval: 30_000,
  });

  const volumeData = (dailyData?.daily_stats ?? []).map((d: any) => ({
    date: d.date?.slice(5) ?? d.date,
    Enrollment:    Math.round((d.total_count ?? 0) * 0.25),
    Verification:  d.successful_count ?? 0,
    Liveness:      Math.round((d.successful_count ?? 0) * 0.6),
    Sessions:      Math.round((d.total_count ?? 0) * 0.4),
  }));

  const successRateData = (dailyData?.daily_stats ?? []).map((d: any) => {
    const total = d.total_count ?? 1;
    const success = d.successful_count ?? 0;
    return {
      date: d.date?.slice(5) ?? d.date,
      Rate: total > 0 ? +((success / total) * 100).toFixed(2) : 0,
    };
  });

  const totalReqs = GEO_DATA.reduce((a, b) => a + b.requests, 0);

  return (
    <div className="max-w-[1200px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-[22px] font-semibold text-white tracking-tight">Analytics</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)] mt-1">
            Authentication volume, success rates, geographic distribution, and device analytics.
          </p>
        </div>
        <RangeSelector range={range} setRange={setRange} />
      </motion.div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Auth Volume",     value: overview?.total_transactions ?? 0, suffix: "", color: "#00C2FF", icon: Activity },
          { label: "Success Rate",    value: overview?.authorization_rate ?? 0, suffix: "%", decimals: 1, color: "#00E5A8", icon: ShieldCheck },
          { label: "Active Users",    value: userStats?.active_users ?? 0,      suffix: "", color: "#818cf8", icon: Users },
          { label: "Avg Latency",     value: 61,                                suffix: "ms", color: "#fbbf24", icon: Zap },
        ].map((k, i) => (
          <motion.div key={k.label}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07 }}
            className="dash-card p-5 rounded-2xl">
            <div className="flex items-center justify-between mb-3">
              <p className="kpi-label">{k.label}</p>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{ background: `${k.color}12`, border: `1px solid ${k.color}20` }}>
                <k.icon size={12} style={{ color: k.color }} />
              </div>
            </div>
            <p className="text-[28px] font-bold" style={{ color: k.color }}>
              {(k as any).decimals
                ? (k.value as number).toFixed((k as any).decimals)
                : Number(k.value).toLocaleString()}
              {k.suffix}
            </p>
            <p className="text-[10px] text-[#00E5A8] mt-1.5 flex items-center gap-0.5">
              <ArrowUpRight size={9} /> +12% vs last period
            </p>
          </motion.div>
        ))}
      </div>

      {/* Volume + Success Rate charts */}
      <div className="grid xl:grid-cols-[1fr_340px] gap-4">
        {/* Volume Chart */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="dash-card p-6 rounded-2xl">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-[14px] font-semibold text-white">Authentication Volume</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Requests per day by type</p>
            </div>
          </div>
          {isLoading ? (
            <div className="h-[220px] animate-pulse rounded-xl" style={{ background: "rgba(255,255,255,0.04)" }} />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={volumeData} margin={{ top: 4, right: 0, left: -20, bottom: 0 }} barGap={2} barCategoryGap="30%">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} width={32} />
                <Tooltip content={<ChartTip />} />
                <Bar dataKey="Enrollment"   name="Enrollment"   fill="#00C2FF" radius={[3,3,0,0]} opacity={0.85} />
                <Bar dataKey="Verification" name="Verification" fill="#00E5A8" radius={[3,3,0,0]} opacity={0.85} />
                <Bar dataKey="Liveness"     name="Liveness"     fill="#818cf8" radius={[3,3,0,0]} opacity={0.85} />
              </BarChart>
            </ResponsiveContainer>
          )}
          <div className="flex flex-wrap gap-4 mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            {[["#00C2FF","Enrollment"],["#00E5A8","Verification"],["#818cf8","Liveness"]].map(([c,l]) => (
              <span key={l} className="flex items-center gap-1.5 text-[10.5px] text-[rgba(255,255,255,0.35)]">
                <span className="w-2.5 h-2.5 rounded-sm" style={{ background: c }} />{l}
              </span>
            ))}
          </div>
        </motion.div>

        {/* Success Rate Trend */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="dash-card p-6 rounded-2xl">
          <div className="mb-5">
            <h2 className="text-[14px] font-semibold text-white">Verification Success Rate</h2>
            <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Daily pass rate %</p>
          </div>
          {isLoading ? (
            <div className="h-[220px] animate-pulse rounded-xl" style={{ background: "rgba(255,255,255,0.04)" }} />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={successRateData} margin={{ top: 4, right: 0, left: -24, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} width={32} domain={[80, 100]} unit="%" />
                <Tooltip content={<ChartTip />} />
                <Line type="monotone" dataKey="Rate" name="Success Rate" stroke="#00E5A8" strokeWidth={2} dot={{ fill: "#00E5A8", r: 3, strokeWidth: 0 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </motion.div>
      </div>

      {/* Geo Distribution + Device Breakdown */}
      <div className="grid xl:grid-cols-2 gap-4">
        {/* Geographic Distribution */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="dash-card rounded-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <Globe size={14} style={{ color: "rgba(255,255,255,0.3)" }} />
            <div>
              <h2 className="text-[14px] font-semibold text-white">Geographic Distribution</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Top countries by API requests</p>
            </div>
          </div>
          <div className="p-5 space-y-3">
            {GEO_DATA.map((g, i) => {
              const pct = Math.round((g.requests / totalReqs) * 100);
              return (
                <motion.div key={g.country}
                  initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.42 + i * 0.05 }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[12.5px] text-[rgba(255,255,255,0.7)]">{g.country}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono text-[rgba(255,255,255,0.4)]">{g.requests.toLocaleString()}</span>
                      <span className="text-[10px] font-semibold min-w-[28px] text-right" style={{ color: g.color }}>{pct}%</span>
                    </div>
                  </div>
                  <div className="h-1 w-full rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                    <motion.div className="h-full rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.7, delay: 0.45 + i * 0.06 }}
                      style={{ background: g.color }} />
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Device Analytics */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="dash-card p-6 rounded-2xl">
          <div className="flex items-center gap-2 mb-5">
            <Smartphone size={14} style={{ color: "rgba(255,255,255,0.3)" }} />
            <div>
              <h2 className="text-[14px] font-semibold text-white">Device Analytics</h2>
              <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Platform breakdown</p>
            </div>
          </div>
          <div className="flex items-center gap-8">
            {/* Donut */}
            <div className="shrink-0">
              <ResponsiveContainer width={140} height={140}>
                <PieChart>
                  <Pie data={DEVICE_DATA} cx="50%" cy="50%" innerRadius={45} outerRadius={65}
                    dataKey="value" strokeWidth={0}>
                    {DEVICE_DATA.map((d, i) => (
                      <Cell key={i} fill={d.color} opacity={0.85} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            </div>
            {/* Legend */}
            <div className="flex-1 space-y-3">
              {DEVICE_DATA.map((d, i) => (
                <motion.div key={d.name}
                  initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.07 }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="flex items-center gap-2 text-[12.5px] text-[rgba(255,255,255,0.65)]">
                      <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                      {d.name}
                    </span>
                    <span className="text-[12px] font-semibold" style={{ color: d.color }}>{d.value}%</span>
                  </div>
                  <div className="h-0.5 w-full rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                    <div className="h-full rounded-full" style={{ width: `${d.value}%`, background: d.color }} />
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Fraud Detection Metrics */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="dash-card p-6 rounded-2xl"
        style={{ borderColor: "rgba(248,113,113,0.1)" }}>
        <div className="mb-5">
          <h2 className="text-[14px] font-semibold text-white">Fraud Detection Summary</h2>
          <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Spoof, deepfake, and replay attack metrics</p>
        </div>
        <div className="grid sm:grid-cols-4 gap-4">
          {[
            { label: "Spoof Block Rate",    value: "99.8%", color: "#00E5A8", desc: "Spoofs successfully blocked" },
            { label: "Deepfake Accuracy",   value: "97.3%", color: "#00C2FF", desc: "Deepfakes correctly identified" },
            { label: "Replay Prevention",   value: "99.6%", color: "#818cf8", desc: "Replay attacks prevented" },
            { label: "False Positive Rate", value: "0.04%", color: "#fbbf24", desc: "Legitimate users blocked" },
          ].map((m, i) => (
            <div key={m.label} className="p-4 rounded-xl"
              style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.06)" }}>
              <p className="text-[10px] text-[rgba(255,255,255,0.3)] uppercase tracking-wider mb-2">{m.label}</p>
              <p className="text-[24px] font-bold mb-1" style={{ color: m.color }}>{m.value}</p>
              <p className="text-[10.5px] text-[rgba(255,255,255,0.3)] leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
