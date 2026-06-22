"use client";
import { useRef, useEffect, useCallback } from "react";
import { motion, useScroll, useTransform, useSpring, useMotionValue } from "framer-motion";
import Link from "next/link";
import Image from "next/image";

/* ── Trust Chips ──────────────────────────────────────────────────────────── */
const TRUST_CHIPS = [
  "Face Recognition",
  "Iris Authentication",
  "Fingerprint Payments",
  "Liveness Detection",
  "Merchant APIs",
  "Banking Grade",
];

/* ── Floating Cards ───────────────────────────────────────────────────────── */
function FloatingCard({
  children,
  className,
  delay,
  floatAmplitude = 5,
  floatDuration = 4,
}: {
  children: React.ReactNode;
  className?: string;
  delay: number;
  floatAmplitude?: number;
  floatDuration?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ delay, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className={`absolute z-30 ${className}`}
    >
      <motion.div
        animate={{ y: [0, -floatAmplitude, 0] }}
        transition={{ duration: floatDuration, repeat: Infinity, ease: "easeInOut" }}
        className="backdrop-blur-xl bg-black/70 border border-white/[0.1] rounded-xl px-3.5 py-2.5 shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

/* ── Main Hero ────────────────────────────────────────────────────────────── */
export function HeroSection() {
  const sectionRef = useRef<HTMLElement>(null);

  // Parallax cursor
  const springCfg = { stiffness: 45, damping: 22, mass: 0.6 };
  const videoX = useSpring(useMotionValue(0), springCfg);
  const videoY = useSpring(useMotionValue(0), springCfg);
  const cardX = useSpring(useMotionValue(0), { stiffness: 28, damping: 18 });
  const cardY = useSpring(useMotionValue(0), { stiffness: 28, damping: 18 });

  const onMouseMove = useCallback((e: MouseEvent) => {
    const rect = sectionRef.current?.getBoundingClientRect();
    if (!rect) return;
    const dx = (e.clientX - rect.left - rect.width / 2) / (rect.width / 2);
    const dy = (e.clientY - rect.top - rect.height / 2) / (rect.height / 2);
    videoX.set(dx * 10);
    videoY.set(dy * 7);
    cardX.set(dx * 16);
    cardY.set(dy * 12);
  }, [videoX, videoY, cardX, cardY]);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    el.addEventListener("mousemove", onMouseMove);
    return () => el.removeEventListener("mousemove", onMouseMove);
  }, [onMouseMove]);

  // Scroll parallax
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start start", "end start"] });
  const vidScale = useTransform(scrollYProgress, [0, 0.6], [1, 0.88]);
  const vidOpacity = useTransform(scrollYProgress, [0, 0.6], [1, 0]);
  const leftY = useTransform(scrollYProgress, [0, 0.5], [0, -32]);
  const leftOp = useTransform(scrollYProgress, [0, 0.4], [1, 0]);

  return (
    <section
      ref={sectionRef}
      className="relative w-full min-h-screen flex items-center bg-[#000000] overflow-hidden"
    >
      {/* Grid */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.4 }}
        className="absolute inset-0 pointer-events-none opacity-[0.4]"
        style={{
          backgroundImage: `radial-gradient(circle at center, rgba(255,255,255,0.15) 1.5px, transparent 1.5px)`,
          backgroundSize: "32px 32px",
          maskImage: "linear-gradient(to bottom, black 0%, black 60%, transparent 100%)",
          WebkitMaskImage: "linear-gradient(to bottom, black 0%, black 60%, transparent 100%)",
        }}
      />

      {/* Atmosphere */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 60% 55% at 72% 50%, rgba(0,229,168,0.05) 0%, transparent 65%),
            radial-gradient(ellipse 35% 40% at 18% 55%, rgba(0,194,255,0.02) 0%, transparent 65%)
          `,
        }}
      />
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.015] mix-blend-overlay pointer-events-none" />

      {/* ── Content wrapper ── */}
      <div className="w-full max-w-[1440px] mx-auto px-6 lg:px-12 py-24 relative z-10 min-h-screen flex items-center">
        <div className="w-full grid lg:grid-cols-[44fr_56fr] gap-10 lg:gap-16 items-center">

          {/* ════════ LEFT: COPY ════════ */}
          <motion.div style={{ y: leftY, opacity: leftOp }} className="flex flex-col">

            {/* Logo */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="mb-8"
            >
              <Image src="/logo.png" alt="NeoFace Logo" width={320} height={96} className="h-30 w-auto object-contain" />
            </motion.div>

            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              className="mb-6"
            >
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-[#00E5A8]/20 bg-[#00E5A8]/[0.06] text-[#00E5A8] text-[11px] font-semibold tracking-wide">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A8] animate-pulse flex-shrink-0" />
                Biometric Payment Infrastructure
              </div>
            </motion.div>

            {/* Headline — tight, premium */}
            <div className="mb-6 overflow-hidden">
              <motion.h1
                className="font-bold text-white tracking-[-0.03em] leading-[1.08]"
                style={{ fontSize: "clamp(40px, 4.8vw, 68px)" }}
              >
                <motion.span
                  className="block"
                  initial={{ y: "110%", opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                >
                  Payments.
                </motion.span>
                <motion.span
                  className="block text-white/60"
                  initial={{ y: "110%", opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                >
                  Powered By You.
                </motion.span>
              </motion.h1>
            </div>

            {/* Sub */}
            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.42, ease: [0.16, 1, 0.3, 1] }}
              className="text-[15px] lg:text-[16px] text-white/44 leading-[1.72] max-w-[460px] mb-8 font-normal"
              style={{ color: "rgba(255,255,255,0.44)" }}
            >
              Transform your face, iris, and fingerprint into a secure payment credential.
              Authorize transactions instantly — no cards, no phones, no PINs.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.58, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-wrap items-center gap-3 mb-9"
            >
              <Link href="/enroll">
                <motion.button
                  whileHover={{ scale: 1.03, boxShadow: "0 10px 36px rgba(255,255,255,0.18)" }}
                  whileTap={{ scale: 0.97 }}
                  className="px-6 py-3 rounded-full bg-white text-black font-semibold text-[13.5px] flex items-center gap-2 shadow-[0_6px_24px_rgba(255,255,255,0.1)]"
                >
                  Start Building
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M1.5 6h9M7 2.5L10.5 6 7 9.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </motion.button>
              </Link>

              <Link href="#product">
                <motion.button
                  whileHover={{ scale: 1.03, backgroundColor: "rgba(255,255,255,0.07)" }}
                  whileTap={{ scale: 0.97 }}
                  className="px-6 py-3 rounded-full border border-white/[0.11] bg-white/[0.04] text-white font-medium text-[13.5px] backdrop-blur-md transition-colors"
                >
                  Watch Demo
                </motion.button>
              </Link>
            </motion.div>

            {/* Trust chips */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.82, duration: 0.6 }}
              className="flex flex-wrap gap-2"
            >
              {TRUST_CHIPS.map((chip, i) => (
                <motion.div
                  key={chip}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.88 + i * 0.055, duration: 0.45 }}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-white/[0.07] bg-white/[0.02]"
                >
                  <div className="w-1 h-1 rounded-full bg-[#00E5A8]/70 flex-shrink-0" />
                  <span className="text-[10.5px] font-medium text-white/50 tracking-wide whitespace-nowrap">{chip}</span>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>

          {/* ════════ RIGHT: VIDEO ════════ */}
          <div className="relative flex items-center justify-center h-[420px] sm:h-[500px] lg:h-[640px]">

            {/* Volumetric glow */}
            <motion.div
              initial={{ opacity: 0, scale: 0.75 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.5, duration: 1.8, ease: [0.16, 1, 0.3, 1] }}
              className="absolute inset-0 pointer-events-none"
              style={{
                background: "radial-gradient(ellipse 85% 80% at 50% 52%, rgba(0,229,168,0.11) 0%, rgba(0,194,255,0.05) 40%, transparent 70%)",
                filter: "blur(36px)",
              }}
            />
            <motion.div
              animate={{ opacity: [0.4, 0.75, 0.4], scale: [0.96, 1.04, 0.96] }}
              transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
              className="absolute inset-[12%] pointer-events-none"
              style={{
                background: "radial-gradient(ellipse 60% 60% at 50% 50%, rgba(0,229,168,0.07) 0%, transparent 65%)",
                filter: "blur(50px)",
              }}
            />

            {/* Glass video terminal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.94, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
              style={{ x: videoX, y: videoY, scale: vidScale, opacity: vidOpacity }}
              className="relative w-full h-full"
            >
              {/* Container */}
              <div
                className="relative w-full h-full overflow-hidden"
                style={{
                  borderRadius: "28px",
                  background: "rgba(5,5,5,0.75)",
                  border: "1px solid rgba(255,255,255,0.07)",
                  boxShadow: `
                    0 0 0 1px rgba(0,229,168,0.05),
                    0 28px 72px rgba(0,0,0,0.65),
                    0 0 60px rgba(0,229,168,0.05),
                    inset 0 1px 0 rgba(255,255,255,0.05)
                  `,
                }}
              >
                {/* Ambient inner glow */}
                <motion.div
                  animate={{ opacity: [0.5, 0.85, 0.5] }}
                  transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute inset-0 pointer-events-none z-0"
                  style={{
                    background: "radial-gradient(ellipse 75% 70% at 50% 50%, rgba(0,229,168,0.1) 0%, rgba(0,194,255,0.05) 45%, transparent 70%)",
                  }}
                />

                {/* Video */}
                <video
                  autoPlay
                  muted
                  loop
                  playsInline
                  preload="auto"
                  className="relative z-10 w-full h-full object-cover"
                  style={{
                    borderRadius: "27px",
                    filter: "contrast(1.05) brightness(0.95) saturate(1.05)",
                  }}
                >
                  <source src="/ad.mp4" type="video/mp4" />
                </video>

                {/* Vignette */}
                <div
                  className="absolute inset-0 z-20 pointer-events-none"
                  style={{
                    borderRadius: "28px",
                    background: "radial-gradient(ellipse 100% 100% at 50% 50%, transparent 45%, rgba(0,0,0,0.28) 80%, rgba(0,0,0,0.55) 100%)",
                  }}
                />

                {/* Edge fades */}
                <div className="absolute top-0 inset-x-0 h-16 z-20 pointer-events-none" style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.35), transparent)", borderRadius: "28px 28px 0 0" }} />
                <div className="absolute bottom-0 inset-x-0 h-16 z-20 pointer-events-none" style={{ background: "linear-gradient(to top, rgba(0,0,0,0.45), transparent)", borderRadius: "0 0 28px 28px" }} />

                {/* Scan line */}
                <motion.div
                  className="absolute left-6 right-6 h-px z-20 pointer-events-none"
                  style={{ background: "linear-gradient(90deg, transparent, rgba(0,229,168,0.25), transparent)" }}
                  animate={{ top: ["8%", "88%", "8%"] }}
                  transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
                />

                {/* Corner brackets */}
                {["top-3.5 left-3.5", "top-3.5 right-3.5", "bottom-3.5 left-3.5", "bottom-3.5 right-3.5"].map((pos, i) => (
                  <div key={i} className={`absolute ${pos} z-20 pointer-events-none`}>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      {i === 0 && <path d="M0 7V2a2 2 0 012-2h5" stroke="rgba(0,229,168,0.45)" strokeWidth="1.1" strokeLinecap="round" />}
                      {i === 1 && <path d="M14 7V2a2 2 0 00-2-2H7" stroke="rgba(0,229,168,0.45)" strokeWidth="1.1" strokeLinecap="round" />}
                      {i === 2 && <path d="M0 7v5a2 2 0 002 2h5" stroke="rgba(0,229,168,0.45)" strokeWidth="1.1" strokeLinecap="round" />}
                      {i === 3 && <path d="M14 7v5a2 2 0 01-2 2H7" stroke="rgba(0,229,168,0.45)" strokeWidth="1.1" strokeLinecap="round" />}
                    </svg>
                  </div>
                ))}

                {/* Live pill */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 1.6, duration: 0.5 }}
                  className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/55 border border-white/[0.07] backdrop-blur-md"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A8] animate-pulse" />
                  <span className="text-[9.5px] font-mono text-white/45 tracking-[0.12em] uppercase">Live · NeoFace Pay</span>
                </motion.div>
              </div>

              {/* ── Floating cards ── */}

              {/* Payment Approved — top right */}
              <motion.div
                style={{ x: cardX, y: cardY }}
                className="absolute -top-3 -right-3 lg:-top-4 lg:-right-6 z-30"
              >
                <motion.div
                  initial={{ opacity: 0, scale: 0.85, y: 8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ delay: 1.2, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                >
                  <motion.div
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }}
                    className="backdrop-blur-xl bg-black/70 border border-[#00E5A8]/15 rounded-xl px-3 py-2.5 shadow-[0_8px_28px_rgba(0,0,0,0.45),0_0_16px_rgba(0,229,168,0.08)]"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-[#00E5A8]/12 border border-[#00E5A8]/25 flex items-center justify-center flex-shrink-0">
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                          <path d="M2 5l2.5 2.5L8 2.5" stroke="#00E5A8" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </div>
                      <div>
                        <div className="text-[11px] font-semibold text-[#00E5A8] leading-tight">Payment Approved</div>
                        <div className="text-[10px] text-white/40 font-mono mt-0.5">₹1,250 · Verified</div>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              </motion.div>

              {/* Face Recognition — bottom left */}
              <motion.div className="absolute -bottom-3 -left-3 lg:-bottom-4 lg:-left-6 z-30">
                <motion.div
                  initial={{ opacity: 0, scale: 0.85, y: 8 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  transition={{ delay: 1.45, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                >
                  <motion.div
                    animate={{ y: [0, -5, 0] }}
                    transition={{ duration: 5.1, repeat: Infinity, ease: "easeInOut" }}
                    className="backdrop-blur-xl bg-black/70 border border-[#00C2FF]/15 rounded-xl px-3 py-2.5 shadow-[0_8px_28px_rgba(0,0,0,0.45)]"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-[#00C2FF]/10 border border-[#00C2FF]/20 flex items-center justify-center flex-shrink-0">
                        <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                          <rect x="0.5" y="0.5" width="9" height="9" rx="1.5" stroke="#00C2FF" strokeWidth="1" />
                          <circle cx="5" cy="5" r="2" stroke="#00C2FF" strokeWidth="0.9" />
                        </svg>
                      </div>
                      <div>
                        <div className="text-[11px] font-semibold text-[#00C2FF] leading-tight">Face Recognition</div>
                        <div className="text-[10px] text-white/40 font-mono mt-0.5">99.8% Match</div>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              </motion.div>

              {/* Iris — mid right */}
              <motion.div className="absolute top-[42%] -right-3 lg:-right-8 z-30 -translate-y-1/2">
                <motion.div
                  initial={{ opacity: 0, scale: 0.85, x: 8 }}
                  animate={{ opacity: 1, scale: 1, x: 0 }}
                  transition={{ delay: 1.7, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                >
                  <motion.div
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 4.6, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                    className="backdrop-blur-xl bg-black/70 border border-white/[0.09] rounded-xl px-3 py-2.5 shadow-[0_8px_28px_rgba(0,0,0,0.45)]"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-6 h-6 rounded-full bg-white/[0.05] border border-white/10 flex items-center justify-center flex-shrink-0">
                        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
                          <circle cx="5.5" cy="5.5" r="5" stroke="rgba(0,229,168,0.7)" strokeWidth="0.9" />
                          <circle cx="5.5" cy="5.5" r="2.5" stroke="rgba(0,229,168,0.4)" strokeWidth="0.7" />
                          <circle cx="5.5" cy="5.5" r="1" fill="rgba(0,229,168,0.85)" />
                        </svg>
                      </div>
                      <div>
                        <div className="text-[11px] font-semibold text-white/75 leading-tight">Iris Verified</div>
                        <div className="text-[10px] text-white/35 font-mono mt-0.5">Liveness Passed</div>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              </motion.div>

            </motion.div>
          </div>

        </div>
      </div>

      {/* Bottom fade */}
      <div
        className="absolute bottom-0 inset-x-0 h-28 pointer-events-none z-20"
        style={{ background: "linear-gradient(to top, rgba(0,0,0,0.75), transparent)" }}
      />
    </section>
  );
}
