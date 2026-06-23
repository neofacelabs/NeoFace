"use client";
import { motion } from "framer-motion";
import { Server, Cpu, HardDrive, Globe, Wifi, Database, Activity, Zap, CheckCircle2, AlertTriangle } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid } from "recharts";

const BANDWIDTH_DATA = Array.from({ length: 24 }, (_, i) => ({
  hour: `${String(i).padStart(2, "0")}:00`,
  Inbound:  Math.floor(800 + Math.random() * 1200),
  Outbound: Math.floor(400 + Math.random() * 800),
}));

function BwTip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl px-3 py-2.5 text-[11px]"
      style={{ background: "rgba(8,8,8,0.96)", border: "1px solid rgba(255,255,255,0.08)", backdropFilter: "blur(12px)" }}>
      <p className="text-[rgba(255,255,255,0.4)] mb-1.5 text-[10px]">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center gap-2 mb-0.5">
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: p.color }} />
          <span style={{ color: p.color }}>{p.name}: <strong>{p.value} Mbps</strong></span>
        </p>
      ))}
    </div>
  );
}

const REGIONS = [
  { name: "us-east-1",    label: "N. Virginia",  status: "operational", latency: "12ms",  load: "71%" },
  { name: "eu-west-1",    label: "Ireland",       status: "operational", latency: "18ms",  load: "58%" },
  { name: "ap-south-1",   label: "Mumbai",        status: "operational", latency: "24ms",  load: "44%" },
  { name: "ap-southeast-1", label: "Singapore",  status: "degraded",    latency: "89ms",  load: "38%" },
  { name: "us-west-2",    label: "Oregon",        status: "operational", latency: "15ms",  load: "32%" },
  { name: "sa-east-1",    label: "São Paulo",     status: "operational", latency: "31ms",  load: "19%" },
];

const SERVICES = [
  { name: "Authentication API",  status: "operational", uptime: "99.99%" },
  { name: "Enrollment Service",  status: "operational", uptime: "99.97%" },
  { name: "Liveness Engine",     status: "operational", uptime: "99.94%" },
  { name: "Session Manager",     status: "operational", uptime: "99.99%" },
  { name: "Identity Store",      status: "operational", uptime: "99.98%" },
  { name: "Message Queue",       status: "operational", uptime: "99.99%" },
  { name: "Cache Layer",         status: "operational", uptime: "99.96%" },
  { name: "ML Inference",        status: "degraded",    uptime: "98.61%" },
];

const GPU_CLUSTERS = [
  { id: "gpu-cluster-01", region: "us-east-1", gpus: 8, load: "62%", model: "A100 80GB", status: "active" },
  { id: "gpu-cluster-02", region: "eu-west-1", gpus: 4, load: "45%", model: "A100 80GB", status: "active" },
  { id: "gpu-cluster-03", region: "ap-south-1", gpus: 4, load: "38%", model: "T4 16GB",  status: "active" },
];

function StatusPill({ status }: { status: string }) {
  const cfg = {
    operational: { color: "#00E5A8", dot: "status-dot-live",  label: "Operational" },
    degraded:    { color: "#fbbf24", dot: "status-dot-warn",  label: "Degraded" },
    outage:      { color: "#f87171", dot: "status-dot-error", label: "Outage" },
  }[status] ?? { color: "rgba(255,255,255,0.3)", dot: "", label: status };
  return (
    <span className="flex items-center gap-1.5 text-[11px]" style={{ color: cfg.color }}>
      <span className={cfg.dot} />
      {cfg.label}
    </span>
  );
}

export default function InfrastructurePage() {
  return (
    <div className="max-w-[1200px] space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <h1 className="text-[22px] font-semibold text-white tracking-tight">Infrastructure</h1>
            <span className="px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider uppercase"
              style={{ background: "rgba(251,191,36,0.1)", border: "1px solid rgba(251,191,36,0.25)", color: "#fbbf24" }}>
              CLOUD OPS
            </span>
          </div>
          <p className="text-[13px] text-[rgba(255,255,255,0.38)]">
            Global cloud infrastructure, service health, and resource utilization.
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold"
          style={{ background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.15)", color: "#00E5A8" }}>
          <span className="status-dot-live" /> 7/8 Systems Operational
        </div>
      </motion.div>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: "Active Servers",  value: "142",    color: "#00C2FF",  icon: Server },
          { label: "GPU Clusters",    value: "3",      color: "#818cf8",  icon: Cpu },
          { label: "Storage Used",    value: "4.7 TB", color: "#00E5A8",  icon: HardDrive },
          { label: "Bandwidth",       value: "2.1 Gb", color: "#fbbf24",  icon: Wifi },
          { label: "API Regions",     value: "6",      color: "#00C2FF",  icon: Globe },
          { label: "Total Uptime",    value: "99.96%", color: "#00E5A8",  icon: Activity },
        ].map((k, i) => (
          <motion.div key={k.label}
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="dash-card p-4 rounded-2xl">
            <div className="flex items-center justify-between mb-3">
              <p className="kpi-label text-[9.5px]">{k.label}</p>
              <div className="w-6 h-6 rounded-lg flex items-center justify-center"
                style={{ background: `${k.color}12`, border: `1px solid ${k.color}18` }}>
                <k.icon size={11} style={{ color: k.color }} />
              </div>
            </div>
            <p className="text-[20px] font-bold leading-tight" style={{ color: k.color }}>{k.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Bandwidth + Service Health */}
      <div className="grid xl:grid-cols-[1fr_360px] gap-4">
        {/* Bandwidth Chart */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="dash-card p-6 rounded-2xl">
          <div className="mb-5">
            <h2 className="text-[14px] font-semibold text-white">Network Bandwidth</h2>
            <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Inbound / Outbound — 24h</p>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={BANDWIDTH_DATA} margin={{ top: 4, right: 0, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="bwIn" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00C2FF" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#00C2FF" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="bwOut" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00E5A8" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#00E5A8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="hour" tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 9 }} axisLine={false} tickLine={false} interval={5} />
              <YAxis tick={{ fill: "rgba(255,255,255,0.18)", fontSize: 10 }} axisLine={false} tickLine={false} width={32} unit=" M" />
              <Tooltip content={<BwTip />} />
              <Area type="monotone" dataKey="Inbound"  name="Inbound"  stroke="#00C2FF" strokeWidth={1.5} fill="url(#bwIn)"  dot={false} />
              <Area type="monotone" dataKey="Outbound" name="Outbound" stroke="#00E5A8" strokeWidth={1.5} fill="url(#bwOut)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-3 pt-3" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
            <span className="flex items-center gap-1.5 text-[10.5px] text-[rgba(255,255,255,0.35)]">
              <span className="w-4 h-0.5 rounded-full bg-[#00C2FF]" /> Inbound
            </span>
            <span className="flex items-center gap-1.5 text-[10.5px] text-[rgba(255,255,255,0.35)]">
              <span className="w-4 h-0.5 rounded-full bg-[#00E5A8]" /> Outbound
            </span>
          </div>
        </motion.div>

        {/* Service Health */}
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="dash-card rounded-2xl overflow-hidden">
          <div className="px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <h2 className="text-[14px] font-semibold text-white">Service Health</h2>
            <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">All platform services</p>
          </div>
          <div className="p-2">
            {SERVICES.map((svc, i) => (
              <motion.div key={svc.name}
                initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.32 + i * 0.04 }}
                className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-[rgba(255,255,255,0.025)] transition-all">
                <span className="text-[12.5px] text-[rgba(255,255,255,0.65)] font-medium">{svc.name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-[11px] font-mono text-[rgba(255,255,255,0.3)]">{svc.uptime}</span>
                  <StatusPill status={svc.status} />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* API Regions */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="dash-card rounded-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <div>
            <h2 className="text-[14px] font-semibold text-white">API Regions</h2>
            <p className="text-[11px] text-[rgba(255,255,255,0.3)] mt-0.5">Global edge deployment status</p>
          </div>
          <Globe size={16} style={{ color: "rgba(255,255,255,0.2)" }} />
        </div>
        <div className="p-2">
          <table className="dash-table">
            <thead>
              <tr>
                <th>Region</th>
                <th>Location</th>
                <th>Status</th>
                <th>Latency</th>
                <th>Load</th>
              </tr>
            </thead>
            <tbody>
              {REGIONS.map(r => (
                <tr key={r.name}>
                  <td><span className="font-mono text-[11.5px] text-[rgba(255,255,255,0.55)]">{r.name}</span></td>
                  <td><span className="font-medium text-white">{r.label}</span></td>
                  <td><StatusPill status={r.status} /></td>
                  <td><span className="font-mono text-[11.5px]">{r.latency}</span></td>
                  <td>
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
                        <div className="h-full rounded-full"
                          style={{ width: r.load, background: r.status === "degraded" ? "#fbbf24" : "linear-gradient(90deg, #00C2FF, #00E5A8)" }} />
                      </div>
                      <span className="text-[11px] font-mono">{r.load}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>

      {/* GPU Clusters */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.48 }}>
        <h2 className="text-[15px] font-semibold text-white mb-3">GPU Clusters</h2>
        <div className="grid sm:grid-cols-3 gap-3">
          {GPU_CLUSTERS.map((g, i) => (
            <motion.div key={g.id}
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + i * 0.08 }}
              className="dash-card p-5 rounded-2xl"
              style={{ borderColor: "rgba(129,140,248,0.12)" }}>
              <div className="flex items-center justify-between mb-4">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                  style={{ background: "rgba(129,140,248,0.1)", border: "1px solid rgba(129,140,248,0.2)" }}>
                  <Cpu size={16} style={{ color: "#818cf8" }} />
                </div>
                <span className="status-dot-live" />
              </div>
              <p className="text-[13px] font-semibold text-white mb-0.5">{g.id}</p>
              <p className="text-[10.5px] text-[rgba(255,255,255,0.3)] font-mono mb-4">{g.region} · {g.model}</p>
              <div className="flex items-center justify-between text-[11.5px] mb-2">
                <span className="text-[rgba(255,255,255,0.4)]">{g.gpus} GPUs · Load</span>
                <span style={{ color: "#818cf8" }} className="font-semibold">{g.load}</span>
              </div>
              <div className="h-1.5 w-full rounded-full" style={{ background: "rgba(255,255,255,0.07)" }}>
                <div className="h-full rounded-full transition-all"
                  style={{ width: g.load, background: "linear-gradient(90deg, #818cf8, #00C2FF)" }} />
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
