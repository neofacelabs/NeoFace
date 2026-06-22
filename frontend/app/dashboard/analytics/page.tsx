"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend,
} from "recharts";
import { dashboardApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AnalyticsData, VerificationStats } from "@/types";
import { AdminGuard } from "@/components/admin-guard";

const DAYS_OPTIONS = [7, 14, 30, 90];

function ChartTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[rgba(0,0,0,0.92)] border border-[rgba(255,255,255,0.08)] rounded-xl p-3 text-[11px] shadow-modal">
      <p className="text-[rgba(255,255,255,0.4)] mb-1.5">{label}</p>
      {payload.map((p: any) => <p key={p.dataKey} style={{ color: p.color }}>{p.name}: <strong>{p.value}</strong></p>)}
    </div>
  );
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(14);

  const { data: analytics, isLoading } = useQuery<AnalyticsData>({
    queryKey: ["analytics", days],
    queryFn: () => dashboardApi.getAnalytics(days).then(r => r.data),
  });
  const { data: verifyStats } = useQuery<VerificationStats>({
    queryKey: ["dashboard-verifications"],
    queryFn: () => dashboardApi.getVerifications().then(r => r.data),
  });

  const chartData = analytics?.daily_stats?.map(d => ({
    date: d.date.slice(5),
    verified: d.successful,
    failed: d.total - d.successful,
    rate: d.total > 0 ? Math.round((d.successful / d.total) * 100) : 0,
  })) ?? [];

  const pieData = verifyStats ? [
    { name: "Success", value: verifyStats.successful_verifications },
    { name: "Failed",  value: verifyStats.failed_verifications },
  ] : [];

  const sectionClass = "rounded-2xl border border-[rgba(255,255,255,0.07)] bg-[rgba(255,255,255,0.025)] p-5";

  return (
    <AdminGuard>
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Analytics</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.35)] mt-0.5">Verification trends and performance</p>
        </div>
        <div className="flex items-center gap-0.5 p-1 rounded-xl border border-[rgba(255,255,255,0.07)] bg-[rgba(255,255,255,0.02)]">
          {DAYS_OPTIONS.map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150",
                days === d
                  ? "bg-[rgba(124,124,255,0.15)] text-[#a5b4fc] border border-[rgba(124,124,255,0.25)]"
                  : "text-[rgba(255,255,255,0.35)] hover:text-white"
              )}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Main area chart */}
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className={sectionClass}>
        <h2 className="text-sm font-semibold text-white mb-5">Daily Verification Volume</h2>
        {isLoading ? (
          <div className="h-56 rounded-xl bg-[rgba(255,255,255,0.03)] animate-pulse" />
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chartData} margin={{ top: 0, right: 0, left: -22, bottom: 0 }}>
              <defs>
                <linearGradient id="aV" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#a5b4fc" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#a5b4fc" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="aF" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#f87171" stopOpacity={0.18} />
                  <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.22)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.22)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTip />} />
              <Legend wrapperStyle={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", paddingTop: "16px" }} />
              <Area type="monotone" dataKey="verified" name="Verified" stroke="#a5b4fc" strokeWidth={1.8} fill="url(#aV)" />
              <Area type="monotone" dataKey="failed"   name="Failed"   stroke="#f87171" strokeWidth={1.4} fill="url(#aF)" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </motion.div>

      <div className="grid md:grid-cols-2 gap-4">
        {/* Bar chart */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className={sectionClass}>
          <h2 className="text-sm font-semibold text-white mb-5">Daily Success Rate %</h2>
          {isLoading ? (
            <div className="h-48 rounded-xl bg-[rgba(255,255,255,0.03)] animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} margin={{ top: 0, right: 0, left: -22, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.22)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} tick={{ fill: "rgba(255,255,255,0.22)", fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTip />} />
                <Bar dataKey="rate" name="Success %" fill="#818cf8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </motion.div>

        {/* Pie */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className={sectionClass}>
          <h2 className="text-sm font-semibold text-white mb-5">Overall Outcome Split</h2>
          <div className="flex items-center justify-between">
            <ResponsiveContainer width="60%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
                  <Cell fill="#a5b4fc" strokeWidth={0} />
                  <Cell fill="#f87171" strokeWidth={0} />
                </Pie>
                <Tooltip contentStyle={{ background: "rgba(0,0,0,0.92)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "10px", fontSize: "11px" }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-4">
              {pieData.map((item, i) => (
                <div key={item.name}>
                  <div className="flex items-center gap-2 mb-0.5">
                    <div className="w-2 h-2 rounded-full" style={{ background: i === 0 ? "#a5b4fc" : "#f87171" }} />
                    <span className="text-[11px] text-[rgba(255,255,255,0.38)]">{item.name}</span>
                  </div>
                  <p className="text-xl font-bold text-white">{item.value.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
    </AdminGuard>
  );
}
