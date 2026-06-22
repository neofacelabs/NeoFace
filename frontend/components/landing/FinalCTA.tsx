"use client";
import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import Link from "next/link";

export function FinalCTA() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });

  return (
    <section ref={ref} className="relative min-h-[85vh] flex items-center justify-center px-6 overflow-hidden">
      {/* Atmosphere */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 70% 55% at 50% 50%, rgba(0,229,168,0.07) 0%, transparent 55%),
            radial-gradient(ellipse 35% 30% at 25% 75%, rgba(0,194,255,0.04) 0%, transparent 60%),
            radial-gradient(ellipse 30% 28% at 75% 25%, rgba(20,184,166,0.04) 0%, transparent 60%)
          `,
        }}
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

      {/* Top separator */}
      <div className="absolute top-0 inset-x-0 h-px separator" />

      <div className="relative max-w-5xl mx-auto text-center">
        {/* Biometric ring mark */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mb-10"
        >
          <div
            className="w-16 h-16 rounded-full border mx-auto mb-6 flex items-center justify-center"
            style={{
              borderColor: "rgba(0,229,168,0.25)",
              background: "rgba(0,229,168,0.05)",
              boxShadow: "0 0 40px rgba(0,229,168,0.1)",
            }}
          >
            <svg width="28" height="28" viewBox="0 0 36 36" fill="none">
              <circle cx="18" cy="18" r="16" stroke="rgba(0,229,168,0.4)" strokeWidth="0.8"/>
              <circle cx="18" cy="18" r="10" stroke="rgba(0,194,255,0.6)" strokeWidth="0.8"/>
              <circle cx="18" cy="18" r="5"  stroke="rgba(0,229,168,0.8)" strokeWidth="1" fill="rgba(0,229,168,0.08)"/>
              <circle cx="18" cy="18" r="2"  fill="rgba(0,229,168,0.9)"/>
            </svg>
          </div>
          <div className="tag tag-accent inline-flex">The future of payments</div>
        </motion.div>

        {/* Background Grid Visualization */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20" style={{ perspective: 1000 }}>
          <motion.div 
            className="w-[800px] h-[800px] rounded-full border border-white/10"
            style={{ transform: 'rotateX(60deg)' }}
            animate={{ rotateZ: 360 }}
            transition={{ duration: 50, repeat: Infinity, ease: "linear" }}
          >
            <div className="absolute inset-12 rounded-full border border-[#00E5A8]/20 border-dashed" />
            <div className="absolute inset-24 rounded-full border border-white/5" />
            <div className="absolute inset-36 rounded-full border border-[#00C2FF]/20 border-dashed" />
            <div className="absolute top-0 bottom-0 left-1/2 w-px bg-white/10" />
            <div className="absolute left-0 right-0 top-1/2 h-px bg-white/10" />
          </motion.div>
        </div>

        {/* Headline */}
        <div className="overflow-hidden mb-10 relative z-10">
          <motion.h2
            initial={{ opacity: 0, y: 70 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 1, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="text-[clamp(3.5rem,7vw,7.5rem)] font-bold tracking-tighter text-white leading-none"
            style={{ letterSpacing: "-0.045em" }}
          >
            Building The Future
          </motion.h2>
          <motion.h2
            initial={{ opacity: 0, y: 70 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 1, delay: 0.16, ease: [0.16, 1, 0.3, 1] }}
            className="text-[clamp(3.5rem,7vw,7.5rem)] font-bold tracking-tighter leading-none text-gradient-accent"
            style={{ letterSpacing: "-0.045em" }}
          >
            Of Payments.
          </motion.h2>
        </div>

        {/* Description */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7, delay: 0.35 }}
          className="text-[18px] md:text-[22px] text-[rgba(255,255,255,0.40)] max-w-2xl mx-auto leading-[1.65] mb-12 relative z-10"
        >
          NeoFace is creating the biometric payment layer for the next generation of commerce.
          Face. Iris. Fingerprint.
          <span className="text-white"> One identity. Infinite transactions.</span>
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={inView ? { opacity: 1, y: 0, scale: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.45, ease: [0.16, 1, 0.3, 1] }}
          className="flex items-center justify-center gap-3"
        >
          <Link href="/enroll">
            <motion.button
              whileHover={{ scale: 1.04, boxShadow: "0 0 52px rgba(0,229,168,0.22)" }}
              whileTap={{ scale: 0.97 }}
              className="btn-white text-[15px] font-semibold px-10 py-4"
            >
              Join The Waitlist
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </motion.button>
          </Link>
          <Link href="#developers">
            <motion.button
              whileHover={{ scale: 1.02 }}
              className="btn-ghost px-8 py-4 text-[15px]"
            >
              Book A Demo
            </motion.button>
          </Link>
        </motion.div>

        {/* Payment status */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ delay: 0.7, duration: 0.6 }}
          className="mt-12 flex items-center justify-center gap-6 text-[11px] text-[rgba(255,255,255,0.22)] font-mono"
        >
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A8] animate-pulse" />
            Payment API: Live
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00C2FF] animate-pulse" />
            Avg: 87ms auth
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A8] animate-pulse" />
            Uptime: 99.99%
          </span>
        </motion.div>
      </div>
    </section>
  );
}
