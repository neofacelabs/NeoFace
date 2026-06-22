"use client";
import { useRef, useEffect, useState } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";

const EVENTS = [
  { id: 1, type: "approved",  merchant: "Reliance Fresh", method: "Face",        amount: "₹1,250", time: "just now" },
  { id: 2, type: "approved",  merchant: "Metro Station",  method: "Iris",         amount: "₹35",    time: "2s ago" },
  { id: 3, type: "blocked",   merchant: "Unknown POS",    method: "Face",         amount: "₹8,500", time: "14s ago" },
  { id: 4, type: "approved",  merchant: "Apollo Pharmacy",method: "Fingerprint",  amount: "₹640",   time: "28s ago" },
  { id: 5, type: "approved",  merchant: "HDFC Branch",    method: "Iris",         amount: "₹50,000",time: "1m ago" },
  { id: 6, type: "blocked",   merchant: "Unknown ATM",    method: "Face",         amount: "₹20,000",time: "2m ago" },
  { id: 7, type: "approved",  merchant: "Swiggy Instamart",method: "Face",        amount: "₹420",   time: "3m ago" },
];

const EXTRA_EVENTS = [
  { id: 8,  type: "approved", merchant: "Big Bazaar",    method: "Iris",         amount: "₹3,100", time: "just now" },
  { id: 9,  type: "blocked",  merchant: "Suspect POS",   method: "Face",         amount: "₹15,000",time: "just now" },
  { id: 10, type: "approved", merchant: "Ola Cab",       method: "Fingerprint",  amount: "₹180",   time: "just now" },
];

function PaymentRow({ event, index }: { event: typeof EVENTS[0]; index: number }) {
  const color = event.type === "approved" ? "#00E5A8" : "#f87171";
  const label = event.type === "approved" ? "APPROVED" : "BLOCKED";

  return (
    <motion.div
      initial={{ opacity: 0, x: -16, height: 0 }}
      animate={{ opacity: 1, x: 0, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.4, delay: index * 0.04, ease: [0.16, 1, 0.3, 1] }}
      className="flex items-center gap-4 px-4 py-3 border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors"
    >
      <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold" style={{ color }}>{label}</span>
          <span className="text-[10px] text-[rgba(255,255,255,0.25)] font-mono">{event.method}</span>
        </div>
        <div className="text-[11px] text-[rgba(255,255,255,0.3)] font-mono mt-0.5">{event.merchant}</div>
      </div>
      <div className="flex-shrink-0 text-right">
        <div className="text-[11px] font-mono font-semibold" style={{ color: `${color}cc` }}>{event.amount}</div>
        <div className="text-[10px] text-[rgba(255,255,255,0.22)] mt-0.5">{event.time}</div>
      </div>
    </motion.div>
  );
}

function PaymentAnalyticsTab() {
  const [hoveredBar, setHoveredBar] = useState<number | null>(null);
  const DATA = [
    { label: "Mon", v: 3120, f: 8 },
    { label: "Tue", v: 4800, f: 5 },
    { label: "Wed", v: 4200, f: 11 },
    { label: "Thu", v: 6800, f: 4 },
    { label: "Fri", v: 7900, f: 7 },
    { label: "Sat", v: 9540, f: 9 },
    { label: "Sun", v: 8620, f: 6 },
  ];
  const max = Math.max(...DATA.map(d => d.v));

  return (
    <div className="p-4 space-y-6">
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Payments", val: "₹2.4Cr", color: "#00E5A8", delta: "+18%" },
          { label: "Approval Rate", val: "98.4%", color: "#00E5A8", delta: "+0.6%" },
          { label: "Fraud Blocked", val: "247", color: "#f87171", delta: "−12%" },
        ].map(stat => (
          <div key={stat.label} className="bg-[rgba(255,255,255,0.03)] rounded-xl p-3 border border-[rgba(255,255,255,0.06)]">
            <div className="text-[10px] text-[rgba(255,255,255,0.35)] mb-1.5">{stat.label}</div>
            <div className="text-lg font-bold font-mono" style={{ color: stat.color }}>{stat.val}</div>
            <div className="text-[10px] text-[rgba(255,255,255,0.25)] mt-1">{stat.delta} this week</div>
          </div>
        ))}
      </div>

      {/* Bar chart */}
      <div>
        <div className="text-[11px] text-[rgba(255,255,255,0.35)] mb-3 font-medium">Payment Volume — 7 days</div>
        <div className="flex items-end gap-2 h-32">
          {DATA.map((d, i) => (
            <div
              key={i}
              className="flex-1 flex flex-col items-center gap-1 cursor-pointer"
              onMouseEnter={() => setHoveredBar(i)}
              onMouseLeave={() => setHoveredBar(null)}
            >
              <div className="relative w-full">
                {hoveredBar === i && (
                  <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-[rgba(0,0,0,0.9)] border border-[rgba(255,255,255,0.1)] rounded-lg px-2 py-1 text-[10px] font-mono text-white whitespace-nowrap z-10">
                    ₹{(d.v * 100).toLocaleString()}
                  </div>
                )}
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: `${(d.v / max) * 100}%` }}
                  transition={{ duration: 0.8, delay: i * 0.06, ease: [0.16, 1, 0.3, 1] }}
                  className="rounded-t w-full"
                  style={{
                    background: hoveredBar === i
                      ? "linear-gradient(to top, #00E5A8, #00E5A8)"
                      : "linear-gradient(to top, rgba(0,229,168,0.5), rgba(0,229,168,0.3))",
                    minHeight: 4,
                  }}
                />
              </div>
              <div className="text-[9px] text-[rgba(255,255,255,0.25)]">{d.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function APILogsTab() {
  const LOGS = [
    { method: "POST", path: "/payments/authorize", status: 200, ms: 87,  merchant: "Reliance" },
    { method: "POST", path: "/payments/authorize", status: 401, ms: 42,  merchant: "Unknown" },
    { method: "GET",  path: "/payments/events",   status: 200, ms: 12,  merchant: "HDFC" },
    { method: "POST", path: "/biometric/enroll",   status: 200, ms: 234, merchant: "Merchant" },
    { method: "POST", path: "/payments/authorize", status: 200, ms: 91,  merchant: "Apollo" },
    { method: "GET",  path: "/payments/health",   status: 200, ms: 3,   merchant: "srv_api" },
  ];

  return (
    <div className="p-2 font-mono text-[11px]">
      {LOGS.map((log, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05, duration: 0.3 }}
          className="flex items-center gap-3 px-3 py-2.5 border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)]"
        >
          <span className={`font-semibold text-[10px] w-8 ${log.method === "GET" ? "text-[#00C2FF]" : "text-[#fbbf24]"}`}>
            {log.method}
          </span>
          <span className="text-[rgba(255,255,255,0.6)] flex-1">{log.path}</span>
          <span className={`font-semibold ${log.status === 200 ? "text-[#00E5A8]" : "text-[#f87171]"}`}>
            {log.status}
          </span>
          <span className="text-[rgba(255,255,255,0.25)] w-14 text-right">{log.ms}ms</span>
          <span className="text-[rgba(255,255,255,0.2)] w-20 text-right">{log.merchant}</span>
        </motion.div>
      ))}
    </div>
  );
}

const TABS = ["Live Payments", "Analytics", "API Logs"] as const;

export function ProductSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const [activeTab, setActiveTab] = useState<typeof TABS[number]>("Live Payments");
  const [events, setEvents] = useState(EVENTS);

  // Simulate live payment events
  useEffect(() => {
    if (!inView) return;
    let i = 0;
    const interval = setInterval(() => {
      const newEvent = { ...EXTRA_EVENTS[i % EXTRA_EVENTS.length], id: Date.now() };
      setEvents(prev => [newEvent, ...prev.slice(0, 8)]);
      i++;
    }, 2200);
    return () => clearInterval(interval);
  }, [inView]);

  return (
    <section id="product" ref={ref} className="relative section-pad px-6">
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse 60% 50% at 30% 50%, rgba(0,229,168,0.03) 0%, transparent 65%)" }}
      />
      {/* ── Subtle Dot Grid Pattern ── */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-100"
        style={{
          backgroundImage: `radial-gradient(circle at center, rgba(255,255,255,0.15) 1.5px, transparent 1.5px)`,
          backgroundSize: '32px 32px',
          maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 15%, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 15%, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)'
        }}
      />

      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
          className="mb-16"
        >
          <div className="tag tag-accent inline-flex mb-6">Payment operations</div>
          <h2 className="text-title-1 text-white mb-5 max-w-lg">
            Payments In<br />
            <span className="text-gradient-accent">Real Time.</span>
          </h2>
          <p className="text-[16px] text-[rgba(255,255,255,0.4)] leading-[1.65] max-w-md">
            Monitor biometric transactions, approvals, risk signals, and payment activity from a unified dashboard.
          </p>
        </motion.div>

        {/* Payment Operations Dashboard */}
        <motion.div
          initial={{ opacity: 0, y: 48, scale: 0.98 }}
          animate={inView ? { opacity: 1, y: 0, scale: 1 } : {}}
          transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-3xl border border-[rgba(255,255,255,0.08)] overflow-hidden shadow-modal bg-[#080808]"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.015)]">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
                <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
                <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
              </div>
              <span className="text-[11px] font-mono text-[rgba(255,255,255,0.4)] ml-2">NeoFace Payment Operations</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A8] animate-pulse" />
              <span className="text-[11px] text-[#00E5A8] font-mono">SYSTEM HEALTH: OPTIMAL</span>
            </div>
          </div>

          <div className="p-4 grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Live Payment Stream */}
            <div className="col-span-12 lg:col-span-7 bg-[#0a0a0a] border border-white/5 rounded-2xl overflow-hidden flex flex-col h-[340px]">
              <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
                <div className="text-[10px] text-white/40 font-mono">LIVE PAYMENT STREAM</div>
                <div className="text-[10px] text-white/40 font-mono flex gap-2">
                  <span>TPS: 840</span>
                  <span className="text-[#00E5A8]">UPTIME: 99.999%</span>
                </div>
              </div>
              <div className="flex-1 overflow-hidden flex flex-col relative">
                <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-[#0a0a0a] to-transparent z-10 pointer-events-none" />
                <AnimatePresence initial={false}>
                  {events.slice(0, 6).map((event, i) => (
                    <PaymentRow key={event.id} event={event} index={i} />
                  ))}
                </AnimatePresence>
              </div>
            </div>

            {/* Fraud Intelligence */}
            <div className="col-span-12 lg:col-span-5 bg-[#0a0a0a] border border-white/5 rounded-2xl overflow-hidden flex flex-col h-[340px] relative">
              <div className="px-4 py-3 border-b border-white/5 relative z-10">
                <div className="text-[10px] text-white/40 font-mono">FRAUD INTELLIGENCE</div>
              </div>
              <div className="flex-1 relative flex items-center justify-center p-6">
                {/* Radar Grid */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  {[2, 4, 6].map((ring) => (
                    <div 
                      key={ring} 
                      className="absolute rounded-full border border-[#00E5A8]/10"
                      style={{ width: ring * 40, height: ring * 40 }}
                    />
                  ))}
                  {/* Radar sweep */}
                  <motion.div
                    className="absolute w-[120px] h-[120px] origin-bottom-right"
                    style={{ background: 'conic-gradient(from 0deg, transparent 0deg, rgba(0,229,168,0.2) 90deg, transparent 90deg)', top: '50%', left: '0', marginTop: '-120px' }}
                    animate={{ rotate: 360 }}
                    transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                  />
                </div>

                <div className="w-full space-y-4 relative z-10">
                  <div className="flex justify-between items-center bg-black/40 border border-white/5 rounded p-2">
                    <div>
                      <div className="text-[10px] text-[#f87171] font-mono">SPOOF ATTEMPT</div>
                      <div className="text-[9px] text-white/40 font-mono mt-0.5">Face Photo Injection / Mumbai</div>
                    </div>
                    <div className="text-[10px] text-white/50">Blocked</div>
                  </div>
                  <div className="flex justify-between items-center bg-black/40 border border-white/5 rounded p-2">
                    <div>
                      <div className="text-[10px] text-[#fbbf24] font-mono">VELOCITY CHECK</div>
                      <div className="text-[9px] text-white/40 font-mono mt-0.5">3 txns in 30s / Delhi NCR</div>
                    </div>
                    <div className="text-[10px] text-white/50">Challenged</div>
                  </div>
                  <div className="flex justify-between items-center bg-black/40 border border-white/5 rounded p-2">
                    <div>
                      <div className="text-[10px] text-[#00E5A8] font-mono">VERIFICATION PASSED</div>
                      <div className="text-[9px] text-white/40 font-mono mt-0.5">All nodes secure</div>
                    </div>
                    <div className="text-[10px] text-[#00E5A8]/50">Passing</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Transactions Per Second Monitor */}
            <div className="col-span-12 bg-[#0a0a0a] border border-white/5 rounded-2xl overflow-hidden flex flex-col h-[200px]">
              <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
                <div className="text-[10px] text-white/40 font-mono">TRANSACTIONS PER SECOND</div>
                <div className="text-[10px] text-white/40 font-mono">GLOBAL AVG: <span className="text-[#00E5A8]">840 TPS</span></div>
              </div>
              <div className="flex-1 p-4 flex items-end gap-1">
                {Array.from({ length: 80 }).map((_, i) => {
                  const isSpike = i % 15 === 0;
                  const height = isSpike ? 60 + Math.random() * 40 : 10 + Math.random() * 20;
                  const color = height > 60 ? "#fbbf24" : "#00E5A8";
                  return (
                    <motion.div
                      key={i}
                      className="flex-1 rounded-t opacity-80"
                      style={{ background: color, minHeight: 2 }}
                      initial={{ height: 0 }}
                      animate={{ height: `${height}%` }}
                      transition={{ duration: 0.5, delay: i * 0.01 }}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
