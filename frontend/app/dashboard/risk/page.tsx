"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck, ShieldAlert, ShieldOff, AlertTriangle, TrendingUp, BarChart3 } from "lucide-react";
import { riskApi } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import { AdminGuard } from "@/components/admin-guard";

function DecisionBadge({ decision }: { decision: string }) {
  const map: Record<string, { color: string; icon: any; label: string }> = {
    approve:  { color: "#00E5A8", icon: ShieldCheck, label: "Approve" },
    step_up:  { color: "#f59e0b", icon: ShieldAlert, label: "Step-Up" },
    reject:   { color: "#f87171", icon: ShieldOff,   label: "Reject"  },
  };
  const cfg = map[decision] ?? map.approve;
  const Icon = cfg.icon;
  return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-[10px] font-semibold"
      style={{ background: `${cfg.color}12`, border: `1px solid ${cfg.color}25`, color: cfg.color }}>
      <Icon size={9} />
      {cfg.label}
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 90 ? "#00E5A8" : score >= 70 ? "#f59e0b" : "#f87171";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-[rgba(255,255,255,0.05)]">
        <motion.div className="h-full rounded-full" style={{ background: color, width: `${score}%` }} />
      </div>
      <span className="text-[11px] font-bold w-7 text-right" style={{ color }}>{score.toFixed(0)}</span>
    </div>
  );
}

export default function RiskHistoryPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["risk-history", page],
    queryFn: () => riskApi.getHistory(page, 20).then(r => r.data),
  });

  const items = (data as any)?.items ?? [];
  const total = (data as any)?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <AdminGuard>
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>

          <h1 className="text-xl font-bold text-white tracking-tight">Trust Score History</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.35)] mt-0.5">
            {total} trust score evaluations · NeoFace Risk Engine
          </p>
        </div>
      </div>

      {/* Stats summary */}
      {items.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Approved", count: items.filter((i: any) => i.decision === "approve").length, color: "#00E5A8" },
            { label: "Step-Up", count: items.filter((i: any) => i.decision === "step_up").length, color: "#f59e0b" },
            { label: "Rejected", count: items.filter((i: any) => i.decision === "reject").length, color: "#f87171" },
          ].map(({ label, count, color }) => (
            <div key={label} className="rounded-2xl p-4 text-center"
              style={{ background: `${color}08`, border: `1px solid ${color}15` }}>
              <div className="text-2xl font-bold" style={{ color }}>{count}</div>
              <div className="text-[10px] text-[rgba(255,255,255,0.3)] mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <div className="rounded-2xl border border-[rgba(255,255,255,0.07)] overflow-hidden"
        style={{ background: "rgba(255,255,255,0.02)" }}>
        <div className="grid grid-cols-12 gap-3 px-5 py-3 border-b border-[rgba(255,255,255,0.06)]">
          {["Decision", "Trust Score", "Face", "Liveness", "Deepfake", "Device", "Time"].map((h, i) => (
            <div key={h} className={cn(
              "text-[10px] font-semibold text-[rgba(255,255,255,0.28)] uppercase tracking-wider",
              i === 0 ? "col-span-2" : i === 1 ? "col-span-2" : i === 6 ? "col-span-2" : "col-span-1"
            )}>{h}</div>
          ))}
        </div>

        {isLoading ? (
          <div className="p-5 space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-10 rounded-xl animate-pulse" style={{ background: "rgba(255,255,255,0.03)" }} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <BarChart3 size={28} style={{ color: "rgba(255,255,255,0.1)" }} />
            <p className="text-[13px] text-[rgba(255,255,255,0.2)]">
              No risk scores yet — run a scan on the Trust Engine or Verify page
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[rgba(255,255,255,0.04)]">
            {items.map((item: any, i: number) => (
              <motion.div key={item.id}
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                className="grid grid-cols-12 gap-3 px-5 py-3.5 hover:bg-[rgba(255,255,255,0.02)] transition-colors">
                <div className="col-span-2 flex items-center"><DecisionBadge decision={item.decision} /></div>
                <div className="col-span-2 flex items-center"><ScoreBar score={item.final_trust_score} /></div>
                <div className="col-span-1 flex items-center">
                  <span className="text-[11px]" style={{ color: item.component_scores?.face != null ? (item.component_scores.face >= 80 ? "#00E5A8" : "#f59e0b") : "rgba(255,255,255,0.2)" }}>
                    {item.component_scores?.face != null ? `${item.component_scores.face.toFixed(0)}` : "—"}
                  </span>
                </div>
                <div className="col-span-1 flex items-center">
                  <span className="text-[11px]" style={{ color: item.component_scores?.liveness != null ? (item.component_scores.liveness >= 70 ? "#00E5A8" : "#f87171") : "rgba(255,255,255,0.2)" }}>
                    {item.component_scores?.liveness != null ? `${item.component_scores.liveness.toFixed(0)}` : "—"}
                  </span>
                </div>
                <div className="col-span-1 flex items-center">
                  <span className="text-[11px]" style={{ color: item.component_scores?.deepfake != null ? (item.component_scores.deepfake >= 80 ? "#00E5A8" : "#f87171") : "rgba(255,255,255,0.2)" }}>
                    {item.component_scores?.deepfake != null ? `${item.component_scores.deepfake.toFixed(0)}` : "—"}
                  </span>
                </div>
                <div className="col-span-1 flex items-center">
                  <span className="text-[11px]" style={{ color: item.component_scores?.device != null ? (item.component_scores.device >= 80 ? "#818cf8" : "#f87171") : "rgba(255,255,255,0.2)" }}>
                    {item.component_scores?.device != null ? `${item.component_scores.device.toFixed(0)}` : "—"}
                  </span>
                </div>
                <div className="col-span-2 flex items-center">
                  <span className="text-[10.5px] text-[rgba(255,255,255,0.25)]">{formatDate(item.created_at)}</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-[12px] text-[rgba(255,255,255,0.3)]">Page {page} of {totalPages}</p>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
              className="w-8 h-8 rounded-lg border border-[rgba(255,255,255,0.07)] flex items-center justify-center text-[rgba(255,255,255,0.4)] hover:text-white disabled:opacity-30 transition-all"
              style={{ fontSize: 12 }}>‹</button>
            <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
              className="w-8 h-8 rounded-lg border border-[rgba(255,255,255,0.07)] flex items-center justify-center text-[rgba(255,255,255,0.4)] hover:text-white disabled:opacity-30 transition-all"
              style={{ fontSize: 12 }}>›</button>
          </div>
        </div>
      )}
    </div>
    </AdminGuard>
  );
}
