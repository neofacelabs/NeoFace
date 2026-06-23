"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Webhook, Plus, CheckCircle2, XCircle, Clock, Copy, RotateCcw, Trash2, ChevronRight } from "lucide-react";
import { toast } from "sonner";

const EVENT_TYPES = [
  "identity.enrolled", "identity.updated",
  "verification.passed", "verification.failed",
  "liveness.passed", "liveness.failed",
  "session.created", "session.expired",
  "threat.detected",
];

const MOCK_WEBHOOKS = [
  {
    id: "wh_01",
    url: "https://api.acme.com/webhooks/neoface",
    events: ["verification.passed", "verification.failed", "liveness.failed"],
    status: "active",
    secret: "whsec_••••••••••••••••",
    created: "Jan 15, 2025",
    lastDelivery: { status: "success", ts: "2 min ago", code: 200 },
    successRate: "99.2%",
    total: 8241,
  },
  {
    id: "wh_02",
    url: "https://hooks.finvault.io/neoface-events",
    events: ["identity.enrolled", "threat.detected"],
    status: "active",
    secret: "whsec_••••••••••••••••",
    created: "Mar 4, 2025",
    lastDelivery: { status: "error", ts: "34 min ago", code: 503 },
    successRate: "94.1%",
    total: 3102,
  },
];

const RECENT_DELIVERIES = [
  { id: "del_a1b2", event: "verification.passed", status: "success", code: 200, ts: "2 min ago",  endpoint: "acme.com" },
  { id: "del_c3d4", event: "liveness.failed",     status: "error",   code: 503, ts: "34 min ago", endpoint: "finvault.io" },
  { id: "del_e5f6", event: "verification.passed", status: "success", code: 200, ts: "1 hr ago",   endpoint: "acme.com" },
  { id: "del_g7h8", event: "identity.enrolled",   status: "success", code: 201, ts: "3 hr ago",   endpoint: "finvault.io" },
  { id: "del_i9j0", event: "threat.detected",     status: "success", code: 200, ts: "5 hr ago",   endpoint: "acme.com" },
];

export default function WebhooksPage() {
  const [showNew, setShowNew] = useState(false);

  return (
    <div className="max-w-[1000px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-[22px] font-semibold text-white tracking-tight">Webhooks</h1>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)] mt-1">
            Configure event delivery endpoints for real-time notifications.
          </p>
        </div>
        <button onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-[12.5px] font-semibold transition-all"
          style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,194,255,0.16)")}
          onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,194,255,0.1)")}>
          <Plus size={13} /> Add Endpoint
        </button>
      </motion.div>

      {/* New endpoint form */}
      {showNew && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="dash-card p-6 rounded-2xl"
          style={{ borderColor: "rgba(0,194,255,0.2)" }}>
          <h3 className="text-[14px] font-semibold text-white mb-4">Add webhook endpoint</h3>
          <div className="space-y-3 mb-4">
            <div>
              <label className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wide block mb-1.5">Endpoint URL</label>
              <input placeholder="https://your-api.com/webhooks/neoface"
                className="w-full px-3.5 py-2.5 rounded-xl text-[13px] text-white outline-none"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)" }}
                onFocus={e => (e.currentTarget.style.borderColor = "rgba(0,194,255,0.35)")}
                onBlur={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)")} />
            </div>
            <div>
              <label className="text-[11px] text-[rgba(255,255,255,0.4)] uppercase tracking-wide block mb-1.5">Events to subscribe</label>
              <div className="flex flex-wrap gap-2">
                {EVENT_TYPES.map(ev => (
                  <label key={ev} className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg cursor-pointer text-[10.5px] text-[rgba(255,255,255,0.45)]"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <input type="checkbox" className="w-2.5 h-2.5 accent-[#00C2FF]" /> {ev}
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => { setShowNew(false); toast.success("Webhook endpoint created"); }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-[12.5px] font-semibold"
              style={{ background: "rgba(0,194,255,0.12)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}>
              <Webhook size={12} /> Create endpoint
            </button>
            <button onClick={() => setShowNew(false)}
              className="px-4 py-2 rounded-xl text-[12.5px] text-[rgba(255,255,255,0.35)]"
              style={{ border: "1px solid rgba(255,255,255,0.08)" }}>
              Cancel
            </button>
          </div>
        </motion.div>
      )}

      {/* Endpoint cards */}
      <div className="space-y-4">
        {MOCK_WEBHOOKS.map((wh, i) => (
          <motion.div key={wh.id}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.09 }}
            className="dash-card rounded-2xl overflow-hidden">
            <div className="flex items-center justify-between flex-wrap gap-3 px-5 py-4"
              style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl flex items-center justify-center"
                  style={{ background: "rgba(0,194,255,0.08)", border: "1px solid rgba(0,194,255,0.15)" }}>
                  <Webhook size={14} style={{ color: "#00C2FF" }} />
                </div>
                <div>
                  <p className="text-[13px] font-semibold text-white font-mono">{wh.url}</p>
                  <p className="text-[10px] text-[rgba(255,255,255,0.28)] mt-0.5">Created {wh.created} · {wh.total.toLocaleString()} total deliveries</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1.5 text-[10.5px]">
                  {wh.lastDelivery.status === "success"
                    ? <><span className="status-dot-live" /><span style={{ color: "#00E5A8" }}>Active</span></>
                    : <><span className="status-dot-error" /><span style={{ color: "#f87171" }}>Error</span></>}
                </span>
                <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10.5px] text-[rgba(255,255,255,0.35)] hover:text-white transition-all"
                  style={{ border: "1px solid rgba(255,255,255,0.07)" }}
                  onClick={() => toast.info("Test delivery sent")}>
                  Send test
                </button>
                <button className="p-1.5 rounded-lg text-[rgba(248,113,113,0.5)] hover:text-[#f87171] transition-all"
                  style={{ border: "1px solid rgba(248,113,113,0.1)" }}>
                  <Trash2 size={11} />
                </button>
              </div>
            </div>

            <div className="px-5 py-4">
              {/* Events subscribed */}
              <p className="kpi-label mb-2">Subscribed Events</p>
              <div className="flex flex-wrap gap-1.5 mb-4">
                {wh.events.map(ev => (
                  <span key={ev} className="text-[10px] px-2 py-0.5 rounded-md font-mono"
                    style={{ background: "rgba(0,194,255,0.06)", border: "1px solid rgba(0,194,255,0.12)", color: "#00C2FF" }}>
                    {ev}
                  </span>
                ))}
              </div>

              {/* Signing secret */}
              <div className="flex items-center gap-2 mb-4">
                <p className="kpi-label">Signing Secret:</p>
                <span className="text-[12px] font-mono text-[rgba(255,255,255,0.4)]">{wh.secret}</span>
                <button onClick={() => toast.success("Copied")} className="text-[rgba(255,255,255,0.25)] hover:text-white transition-colors">
                  <Copy size={11} />
                </button>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "Success Rate",   value: wh.successRate,  color: "#00E5A8" },
                  { label: "Total Delivered",value: wh.total.toLocaleString(), color: "#00C2FF" },
                  { label: "Last Delivery",  value: wh.lastDelivery.ts, color: wh.lastDelivery.status === "success" ? "#00E5A8" : "#f87171" },
                ].map(s => (
                  <div key={s.label} className="p-3 rounded-xl text-center"
                    style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    <p className="text-[14px] font-bold mb-0.5" style={{ color: s.color }}>{s.value}</p>
                    <p className="text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.25)]">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Recent Deliveries */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="dash-card rounded-2xl overflow-hidden">
        <div className="px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <h2 className="text-[14px] font-semibold text-white">Recent Deliveries</h2>
          <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Last delivery attempts across all endpoints</p>
        </div>
        <div className="p-2">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Event</th>
                <th>Endpoint</th>
                <th>Code</th>
                <th>Time</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {RECENT_DELIVERIES.map((d, i) => (
                <motion.tr key={d.id}
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  transition={{ delay: 0.37 + i * 0.04 }}
                  className="cursor-pointer">
                  <td>
                    {d.status === "success"
                      ? <span className="flex items-center gap-1.5 text-[#00E5A8] text-[11.5px]"><CheckCircle2 size={12} /> Success</span>
                      : <span className="flex items-center gap-1.5 text-[#f87171] text-[11.5px]"><XCircle size={12} /> Failed</span>}
                  </td>
                  <td><span className="font-mono text-[11px]">{d.event}</span></td>
                  <td><span className="text-[rgba(255,255,255,0.45)] text-[11.5px]">{d.endpoint}</span></td>
                  <td>
                    <span className="font-mono text-[11px] px-1.5 py-0.5 rounded"
                      style={{ background: d.code === 200 || d.code === 201 ? "rgba(0,229,168,0.08)" : "rgba(248,113,113,0.08)", color: d.code === 200 || d.code === 201 ? "#00E5A8" : "#f87171" }}>
                      {d.code}
                    </span>
                  </td>
                  <td><span className="text-[11.5px] text-[rgba(255,255,255,0.35)]">{d.ts}</span></td>
                  <td>
                    <button className="text-[10px] text-[rgba(0,194,255,0.5)] hover:text-[#00C2FF] transition-colors flex items-center gap-1">
                      Inspect <ChevronRight size={10} />
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
