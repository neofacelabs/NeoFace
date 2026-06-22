"use client";
import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import Image from "next/image";

/* ── Image Visuals ──────────────────────────────────────────────────────────── */
function FaceRecognitionVisual() {
  return (
    <div className="absolute inset-0 w-full h-full scale-[1.25] origin-center pointer-events-none">
      <Image
        src="/Face Detection.png"
        alt="Face Recognition"
        fill
        sizes="(max-width: 768px) 100vw, 50vw"
        className="object-cover"
        style={{ filter: "contrast(1.05) saturate(1.05)" }}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.05), rgba(0,0,0,0.15))" }}
      />
    </div>
  );
}

function IrisVisual() {
  return (
    <div className="absolute inset-0 w-full h-full scale-[1.25] origin-center pointer-events-none">
      <Image
        src="/Iris Detection.png"
        alt="Iris Recognition"
        fill
        sizes="(max-width: 768px) 100vw, 33vw"
        className="object-cover"
        style={{ filter: "contrast(1.05) saturate(1.05)" }}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.05), rgba(0,0,0,0.15))" }}
      />
    </div>
  );
}

function FingerprintVisual() {
  return (
    <div className="absolute inset-0 w-full h-full scale-[1.25] origin-center pointer-events-none">
      <Image
        src="/Fingerprint Detection.png"
        alt="Fingerprint Recognition"
        fill
        sizes="(max-width: 768px) 100vw, 33vw"
        className="object-cover"
        style={{ filter: "contrast(1.05) saturate(1.05)" }}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.05), rgba(0,0,0,0.15))" }}
      />
    </div>
  );
}

function BiometricFusionVisual() {
  return (
    <div className="relative w-full h-full min-h-[280px] aspect-square md:aspect-[4/3] scale-[1.25] origin-center pointer-events-none">
      <Image
        src="/AI Fusion Engine.png"
        alt="Unified Biometric Engine"
        fill
        sizes="(max-width: 768px) 100vw, 66vw"
        className="object-cover"
        style={{ filter: "contrast(1.05) saturate(1.05)" }}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.05), rgba(0,0,0,0.15))" }}
      />
    </div>
  );
}

/* ── Modalities Data ──────────────────────────────────────────────────────── */
const MODALITIES = [
  {
    id: "face",
    title: "Face Recognition",
    subtitle: "Ultra-fast facial payment auth",
    description:
      "Ultra-fast facial authentication with liveness detection and anti-spoof protection. Authorize payments in under 150ms with 99.97% accuracy.",
    color: "#00E5A8",
    spec: "< 150ms · 99.97% accuracy · Anti-spoof",
    visual: <FaceRecognitionVisual />,
  },
  {
    id: "iris",
    title: "Iris Recognition",
    subtitle: "Military-grade verification",
    description:
      "Military-grade identity verification using unique iris patterns. Near-perfect discrimination even between identical twins — at standoff distance.",
    color: "#00C2FF",
    spec: "250+ iris codes · 0.0001% FAR · NIR optimized",
    visual: <IrisVisual />,
  },
  {
    id: "fingerprint",
    title: "Fingerprint Recognition",
    subtitle: "Frictionless fingerprint approval",
    description:
      "Secure fingerprint matching for frictionless payment approvals. Multi-sensor fusion defeats silicon, gelatin, and film spoofing attacks.",
    color: "#00E5A8",
    spec: "< 80ms · Multi-sensor fusion · Anti-spoof hardware",
    visual: <FingerprintVisual />,
  },
  {
    id: "fusion",
    title: "Unified Biometric Engine",
    subtitle: "One decision. Three signals.",
    description:
      "NeoFace fuses all three authentication methods — face, iris, and fingerprint — into a single payment decision engine. Every transaction is authorized through multi-factor biometric verification for maximum security and zero friction.",
    color: "#00C2FF",
    spec: "Multi-factor · Real-time fusion · Payment-grade",
    visual: <BiometricFusionVisual />,
  },
];

function ModalityCard({ mod, index, className = "" }: { mod: typeof MODALITIES[0]; index: number; className?: string }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay: index * 0.1, ease: [0.16, 1, 0.3, 1] }}
      className={`card-premium relative p-6 flex flex-col overflow-hidden group h-full ${className}`}
    >
      {/* Visual Header */}
      <div className="relative w-full flex-1 min-h-[200px] mb-6 rounded-xl bg-[#050505] border border-[rgba(255,255,255,0.05)] flex items-center justify-center overflow-hidden">
        <div
          className="absolute inset-0 opacity-10 blur-2xl group-hover:opacity-30 transition-opacity duration-500"
          style={{ background: mod.color }}
        />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-[0.02] mix-blend-overlay pointer-events-none" />
        <div className="relative w-full h-full transform scale-[0.8] group-hover:scale-[0.85] transition-transform duration-500 flex items-center justify-center">
          {mod.visual}
        </div>
      </div>

      {/* Text Content */}
      <div className="flex-1 flex flex-col">
        <div
          className="text-[10px] font-mono font-semibold uppercase tracking-[0.15em] mb-2"
          style={{ color: mod.color }}
        >
          {mod.subtitle}
        </div>
        <h3 className="text-[18px] font-semibold text-white mb-3">{mod.title}</h3>
        <p className="text-[13px] text-[rgba(255,255,255,0.45)] leading-[1.6] mb-6 flex-1">
          {mod.description}
        </p>
        <div
          className="inline-flex items-center self-start px-3 py-1.5 rounded-full border text-[10px] font-mono"
          style={{
            borderColor: `${mod.color}30`,
            background: `${mod.color}08`,
            color: `${mod.color}cc`,
          }}
        >
          {mod.spec}
        </div>
      </div>
    </motion.div>
  );
}

export function ModalitiesSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });

  return (
    <section id="modalities" ref={ref} className="relative section-pad px-6">
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse 50% 60% at 80% 40%, rgba(103,232,249,0.04) 0%, transparent 65%)" }}
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
          className="mb-16 text-center"
        >
          <div className="tag tag-accent inline-flex mb-6">Biometric payment methods</div>
          <h2 className="text-title-1 text-white max-w-2xl mx-auto">
            Three Biometrics.<br />
            <span className="text-gradient-accent">One Payment Network.</span>
          </h2>
        </motion.div>

        {/* Asymmetrical Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 auto-rows-[minmax(420px,auto)] gap-6 w-full">
          <div className="md:col-span-7">
            <ModalityCard mod={MODALITIES[0]} index={0} />
          </div>
          <div className="md:col-span-5">
            <ModalityCard mod={MODALITIES[1]} index={1} />
          </div>
          
          <div className="md:col-span-4">
            <ModalityCard mod={MODALITIES[2]} index={2} />
          </div>
          <div className="md:col-span-8">
            <ModalityCard mod={MODALITIES[3]} index={3} className="md:flex-row md:items-center gap-8" />
          </div>
        </div>
      </div>
    </section>
  );
}
