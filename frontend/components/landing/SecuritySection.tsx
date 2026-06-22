"use client";
import { useRef } from "react";
import { motion, useInView } from "framer-motion";

function SecurityLayerViz() {
  const LAYERS = [
    { id: 1, label: "Biometric Capture & Anti-Spoofing", sub: "Liveness Detection · Anti-Mask", color: "#00C2FF" },
    { id: 2, label: "Multi-Factor Biometric Fusion", sub: "Face + Iris + Fingerprint", color: "#38BDF8" },
    { id: 3, label: "Payment Authorization Engine", sub: "Risk Scoring · Fraud Analysis", color: "#14B8A6" },
    { id: 4, label: "Transaction Approved & Settled", sub: "₹ Merchant Credited · Receipt Issued", color: "#00E5A8" },
  ];

  return (
    <div className="relative w-full h-[500px] flex items-center justify-center bg-[#050505] rounded-3xl border border-white/5 shadow-2xl overflow-hidden">
      {/* Background Grid */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage: `radial-gradient(circle at center, rgba(255,255,255,0.15) 1px, transparent 1px)`,
          backgroundSize: '24px 24px',
        }}
      />

      {/* Vertical Data Flow Line */}
      <div className="absolute top-10 bottom-10 left-1/2 w-px bg-gradient-to-b from-transparent via-white/10 to-transparent -translate-x-1/2 z-0">
        <motion.div
          className="absolute top-0 left-1/2 w-[2px] h-24 bg-gradient-to-b from-transparent via-[#00E5A8] to-transparent -translate-x-1/2 shadow-[0_0_15px_#00E5A8]"
          animate={{ top: ["0%", "100%"] }}
          transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
        />
      </div>

      <div className="flex flex-col gap-10 relative z-10 w-full max-w-[280px]">
        {LAYERS.map((layer, i) => (
          <motion.div
            key={layer.id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.15 + 0.2, duration: 0.6 }}
            className="group relative bg-black/60 backdrop-blur-xl border border-white/10 rounded-2xl p-4 flex items-center gap-4 hover:border-white/20 transition-colors"
          >
            {/* Glowing Accent */}
            <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-10 transition-opacity" style={{ backgroundColor: layer.color }} />
            
            {/* Left Icon Block */}
            <div className="w-10 h-10 rounded-xl bg-black border flex items-center justify-center shrink-0 relative" style={{ borderColor: `${layer.color}40`, boxShadow: `0 0 15px ${layer.color}15 inset` }}>
              <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: layer.color, boxShadow: `0 0 10px ${layer.color}` }} />
              
              {/* Connector */}
              <div className="absolute -left-[54px] w-2 h-2 rounded-full border-2 border-[#050505]" style={{ backgroundColor: layer.color }} />
              <div className="absolute -left-[54px] w-12 h-px border-t border-dashed border-white/20" />
            </div>

            <div>
              <div className="text-[12px] font-semibold text-white mb-1 leading-tight">{layer.label}</div>
              <div className="text-[9px] font-mono uppercase tracking-[0.1em] text-white/40">{layer.sub}</div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

const SECURITY_PILLARS = [
  {
    title: "Biometric Encryption",
    description: "End-to-end encrypted biometric templates. AES-256-GCM in transit and at rest. No raw biometric data ever stored.",
    color: "#00C2FF",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
        <rect x="3" y="11" width="18" height="11" rx="2" stroke="currentColor" strokeWidth="1.3"/>
        <path d="M7 11V7a5 5 0 0110 0v4" stroke="currentColor" strokeWidth="1.3"/>
        <circle cx="12" cy="16" r="1.5" fill="currentColor"/>
      </svg>
    ),
  },
  {
    title: "Liveness Detection",
    description: "Blocks photos, videos, masks, and spoofing attacks. Real-time 3D liveness analysis with MiniFASNet anti-spoof engine.",
    color: "#00E5A8",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.3"/>
        <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    title: "Fraud Prevention",
    description: "Continuous risk analysis during transactions. Velocity checks, anomaly detection, and cross-network threat intelligence.",
    color: "#14B8A6",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
        <path d="M12 3L5 7v5c0 4.4 3 8.3 7 9 4-.7 7-4.6 7-9V7z" stroke="currentColor" strokeWidth="1.3"/>
        <path d="M9 12l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
  },
  {
    title: "Consent Management",
    description: "User-controlled authentication permissions. Granular biometric consent with right-to-deletion and opt-out at any time.",
    color: "#38BDF8",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="currentColor" strokeWidth="1.3"/>
        <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.3"/>
      </svg>
    ),
  },
  {
    title: "Privacy Architecture",
    description: "Biometric data protection by design. No raw images, no raw scans — only encrypted mathematical vectors.",
    color: "#f87171",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" stroke="currentColor" strokeWidth="1.3"/>
        <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        <line x1="12" y1="17" x2="12.01" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
      </svg>
    ),
  },
  {
    title: "Compliance Ready",
    description: "Built for banking and financial regulations. PCI DSS, RBI guidelines, GDPR, SOC 2 Type II — audited and certified.",
    color: "#00FFD1",
    icon: (
      <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
        <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.3"/>
        <path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
        <path d="M4.9 4.9l2.1 2.1M16.9 16.9l2.1 2.1M4.9 19.1l2.1-2.1M16.9 7.1l2.1-2.1" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      </svg>
    ),
  },
];

export function SecuritySection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section id="security" ref={ref} className="relative section-pad px-6">
      {/* Background atmosphere */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(0,229,168,0.035) 0%, transparent 65%)" }}
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
          className="text-center mb-20"
        >
          <div className="tag tag-accent inline-flex mb-6">Payment security</div>
          <h2 className="text-title-1 text-white mb-5">
            Security At Every Layer.<br />
            <span className="text-gradient-accent">At Every Transaction.</span>
          </h2>
          <p className="text-[16px] text-[rgba(255,255,255,0.4)] max-w-md mx-auto leading-[1.65]">
            Biometric payment infrastructure requires security that goes beyond SSL. NeoFace is built with a concentric trust model from sensor to settlement.
          </p>
        </motion.div>

        {/* Viz + pillars */}
        <div className="grid lg:grid-cols-[1fr_1fr] gap-20 items-center">
          {/* Visualization */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={inView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
          >
            <SecurityLayerViz />
          </motion.div>

          {/* Premium pillars grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SECURITY_PILLARS.map((pillar, i) => (
              <motion.div
                key={pillar.title}
                initial={{ opacity: 0, y: 20 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: 0.1 + i * 0.08, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                className="group card-premium p-5 cursor-default"
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center mb-3 transition-all duration-300"
                  style={{
                    background: `${pillar.color}10`,
                    color: pillar.color,
                    boxShadow: `0 0 16px ${pillar.color}12`,
                  }}
                >
                  {pillar.icon}
                </div>
                <h4 className="text-[13px] font-semibold text-white mb-2 leading-tight">{pillar.title}</h4>
                <p className="text-[12px] text-[rgba(255,255,255,0.36)] leading-[1.6]">{pillar.description}</p>

                {/* Bottom accent line */}
                <div
                  className="absolute bottom-0 left-5 right-5 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                  style={{ background: `linear-gradient(90deg, transparent, ${pillar.color}40, transparent)` }}
                />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
