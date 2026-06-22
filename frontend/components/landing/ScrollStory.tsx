"use client";
import { useRef } from "react";
import { motion, useInView } from "framer-motion";

function StoryVisualLegacy() {
  return (
    <div className="relative w-full h-full flex items-center justify-center bg-black">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(248,113,113,0.1)_0%,transparent_70%)]" />
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03]" />
      
      <div className="relative flex flex-col items-center gap-6">
        {/* Old payment methods fading */}
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "CARD", icon: "💳", opacity: "opacity-30" },
            { label: "PIN", icon: "🔢", opacity: "opacity-25" },
            { label: "QR", icon: "⬛", opacity: "opacity-20" },
            { label: "OTP", icon: "📱", opacity: "opacity-15" },
          ].map(item => (
            <div key={item.label} className={`${item.opacity} bg-[#0a0a0a] border border-[#f87171]/20 rounded-xl p-3 flex flex-col items-center gap-1.5`}>
              <span className="text-lg grayscale">{item.icon}</span>
              <span className="text-[9px] font-mono text-[#f87171]/60 tracking-[0.15em]">{item.label}</span>
              <div className="w-full h-px bg-gradient-to-r from-transparent via-[#f87171]/20 to-transparent" />
              <span className="text-[8px] font-mono text-[#f87171]/40">DEPRECATED</span>
            </div>
          ))}
        </div>

        {/* Warning Badge */}
        <div className="bg-black border border-[#f87171]/30 text-[#f87171] px-4 py-2 rounded-full text-[11px] font-mono font-bold tracking-widest uppercase flex items-center gap-2 shadow-[0_0_20px_rgba(248,113,113,0.2)]">
          <span className="w-1.5 h-1.5 bg-[#f87171] rounded-full animate-pulse" />
          Device-Dependent Era Ending
        </div>
      </div>
    </div>
  );
}

function StoryVisualBiometric() {
  return (
    <div className="relative w-full h-full flex items-center justify-center bg-black">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(0,229,168,0.1)_0%,transparent_70%)]" />
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.03]" />
      
      <div className="relative w-full max-w-[320px]">
        {/* Core Biometric Node */}
        <div className="w-24 h-24 mx-auto bg-black border border-[#00E5A8]/30 rounded-2xl flex items-center justify-center relative z-10 shadow-[0_0_40px_rgba(0,229,168,0.2)]">
          {/* Face mesh mini icon */}
          <svg viewBox="0 0 32 32" className="w-10 h-10" fill="none">
            <ellipse cx="16" cy="16" rx="10" ry="12" stroke="rgba(0,229,168,0.3)" strokeWidth="0.8"/>
            {[10, 13, 16, 19, 22].map(y => (
              <line key={y} x1={`${16 - Math.sqrt(Math.max(0, 100 - (y-16)*(y-16)*0.69))}`} y1={y} x2={`${16 + Math.sqrt(Math.max(0, 100 - (y-16)*(y-16)*0.69))}`} y2={y} stroke="rgba(0,229,168,0.2)" strokeWidth="0.5"/>
            ))}
            <circle cx="12" cy="13" r="1.5" stroke="#00E5A8" strokeWidth="0.8" fill="none"/>
            <circle cx="20" cy="13" r="1.5" stroke="#00E5A8" strokeWidth="0.8" fill="none"/>
          </svg>
          <motion.div
            className="absolute inset-0 border border-[#00E5A8] rounded-2xl"
            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>

        {/* Connecting Lines */}
        <div className="absolute top-12 left-12 right-12 h-px bg-gradient-to-r from-transparent via-[#00E5A8]/50 to-transparent -z-10" />
        <div className="absolute top-12 left-1/2 w-px h-32 bg-gradient-to-b from-[#00E5A8]/50 to-transparent -translate-x-1/2 -z-10" />

        {/* Biometric Signals */}
        <div className="flex justify-between mt-8 relative z-10">
          <div className="bg-[#0a0a0a] border border-[#00E5A8]/20 px-3 py-1.5 rounded text-[10px] text-[#00E5A8]/70 font-mono">FACE</div>
          <div className="bg-[#0a0a0a] border border-[#00C2FF]/20 px-3 py-1.5 rounded text-[10px] text-[#00C2FF]/70 font-mono">IRIS</div>
          <div className="bg-[#0a0a0a] border border-[#00E5A8]/20 px-3 py-1.5 rounded text-[10px] text-[#00E5A8]/70 font-mono">PRINT</div>
        </div>

        <div className="mt-12 text-center text-[10px] font-mono text-[#00E5A8]">
          <motion.div initial={{ opacity: 0.5 }} animate={{ opacity: 1 }} transition={{ duration: 1, repeat: Infinity, repeatType: "reverse" }}>
            ₹ 1,250 · PAYMENT AUTHORIZED
          </motion.div>
        </div>
      </div>
    </div>
  );
}

export function ScrollStory() {
  const ref1 = useRef(null);
  const ref2 = useRef(null);
  const inView1 = useInView(ref1, { once: true, margin: "-100px" });
  const inView2 = useInView(ref2, { once: true, margin: "-100px" });

  return (
    <section id="why-neoface" className="relative py-32 px-6 bg-[#000000] overflow-hidden">
      {/* ── Background Grid ── */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-100"
        style={{
          backgroundImage: `radial-gradient(circle at center, rgba(255,255,255,0.15) 1.5px, transparent 1.5px)`,
          backgroundSize: '32px 32px',
          maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 15%, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 15%, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)'
        }}
      />

      <div className="max-w-[1400px] mx-auto relative z-10">
        
        {/* Intro */}
        <div className="text-center mb-32 md:mb-48">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="text-[clamp(3rem,5vw,5rem)] font-bold tracking-tighter text-white leading-[1.1]"
          >
            Payments Shouldn't <br className="hidden md:block" />
            Require Devices.
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="text-[18px] md:text-[22px] text-white/40 mt-8 max-w-3xl mx-auto leading-relaxed"
          >
            Today's payment systems depend on phones, cards, OTPs, passwords, QR codes, and hardware tokens.
            NeoFace replaces them all with <span className="text-white">biometric identity</span> — one person, one payment layer.
          </motion.p>
        </div>

        {/* Step 1: The Legacy Problem */}
        <div ref={ref1} className="grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-center mb-32 md:mb-48">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView1 ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="text-[#f87171] font-mono text-[11px] font-bold tracking-[0.2em] mb-6">THE PROBLEM</div>
            <h3 className="text-[32px] md:text-[44px] font-bold text-white mb-6 leading-[1.1] tracking-tight">
              Every payment still needs a device.
            </h3>
            <p className="text-[16px] md:text-[18px] text-white/40 leading-[1.7]">
              Cards get lost. Phones die. PINs are forgotten. OTPs arrive late. 
              QR codes fail. Hardware tokens get stolen. The entire device-dependent payment stack 
              creates friction — and risk — at every transaction.
            </p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={inView1 ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="h-[400px] md:h-[500px] rounded-3xl overflow-hidden border border-white/5 shadow-2xl relative"
          >
            <StoryVisualLegacy />
          </motion.div>
        </div>

        {/* Step 2: The NeoFace Solution */}
        <div ref={ref2} className="grid grid-cols-1 lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={inView2 ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="order-2 lg:order-1 h-[400px] md:h-[500px] rounded-3xl overflow-hidden border border-white/5 shadow-2xl relative"
          >
            <StoryVisualBiometric />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView2 ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="order-1 lg:order-2"
          >
            <div className="text-[#00E5A8] font-mono text-[11px] font-bold tracking-[0.2em] mb-6">THE SOLUTION</div>
            <h3 className="text-[32px] md:text-[44px] font-bold text-white mb-6 leading-[1.1] tracking-tight">
              Your identity becomes your wallet.
            </h3>
            <p className="text-[16px] md:text-[18px] text-white/40 leading-[1.7]">
              NeoFace fuses Face, Iris, and Fingerprint into a single payment authorization layer.
              <br/><br/>
              One person. One identity. Infinite transactions — with zero hardware required.
            </p>
          </motion.div>
        </div>

      </div>
    </section>
  );
}
