"use client";
import { motion } from "framer-motion";
import { Scan, User, Wifi } from "lucide-react";
import { useEffect, useState } from "react";

const SCAN_POINTS = [
  { x: 50, y: 20 }, { x: 80, y: 35 }, { x: 85, y: 55 },
  { x: 70, y: 75 }, { x: 50, y: 82 }, { x: 30, y: 75 },
  { x: 15, y: 55 }, { x: 20, y: 35 },
];

export function FaceScanVisual() {
  const [scanY, setScanY] = useState(0);
  const [active, setActive] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setActive(true);
      let y = 0;
      const anim = setInterval(() => {
        y += 1;
        setScanY(y);
        if (y >= 100) {
          clearInterval(anim);
          setTimeout(() => { setScanY(0); setActive(false); }, 800);
        }
      }, 25);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {/* Outer ring */}
      <motion.div
        animate={{ scale: [1, 1.02, 1], opacity: [0.4, 0.7, 0.4] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="absolute w-full h-full rounded-full border border-accent-violet/20"
      />
      <motion.div
        animate={{ scale: [1, 1.05, 1], opacity: [0.2, 0.5, 0.2] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
        className="absolute w-[90%] h-[90%] rounded-full border border-accent-violet/15"
      />

      {/* Main card */}
      <div className="relative w-72 h-72 rounded-3xl glass-strong border border-border-strong overflow-hidden shadow-glow-md">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-accent-violet/10 via-transparent to-purple-500/10" />

        {/* Face outline grid */}
        <div className="absolute inset-0 flex items-center justify-center">
          <svg className="w-48 h-48 opacity-20" viewBox="0 0 100 100">
            {/* Face outline */}
            <ellipse cx="50" cy="45" rx="25" ry="30" fill="none" stroke="#6366f1" strokeWidth="0.5" />
            {/* Eyes */}
            <ellipse cx="38" cy="40" rx="5" ry="3" fill="none" stroke="#6366f1" strokeWidth="0.5" />
            <ellipse cx="62" cy="40" rx="5" ry="3" fill="none" stroke="#6366f1" strokeWidth="0.5" />
            {/* Nose */}
            <path d="M50 43 L47 52 Q50 54 53 52 Z" fill="none" stroke="#6366f1" strokeWidth="0.5" />
            {/* Mouth */}
            <path d="M42 58 Q50 63 58 58" fill="none" stroke="#6366f1" strokeWidth="0.5" />
            {/* Landmark dots */}
            {SCAN_POINTS.map((pt, i) => (
              <motion.circle
                key={i}
                cx={pt.x}
                cy={pt.y}
                r="1.5"
                fill="#6366f1"
                initial={{ opacity: 0 }}
                animate={{ opacity: [0, 1, 0.5, 1] }}
                transition={{ duration: 2, delay: i * 0.15, repeat: Infinity }}
              />
            ))}
            {/* Landmark connections */}
            <polyline
              points={SCAN_POINTS.map(p => `${p.x},${p.y}`).join(" ")}
              fill="none" stroke="#6366f1" strokeWidth="0.3" opacity="0.5"
            />
          </svg>
        </div>

        {/* Scan line */}
        {active && (
          <motion.div
            className="absolute inset-x-4 h-px"
            style={{ top: `${scanY}%` }}
            animate={{ opacity: [0.8, 1, 0.8] }}
            transition={{ duration: 0.1, repeat: Infinity }}
          >
            <div className="w-full h-px bg-gradient-to-r from-transparent via-accent-violet to-transparent" />
            <div className="w-full h-4 -mt-2 bg-gradient-to-b from-accent-violet/20 to-transparent" />
          </motion.div>
        )}

        {/* Corner markers */}
        {[
          "top-4 left-4 border-t border-l",
          "top-4 right-4 border-t border-r",
          "bottom-4 left-4 border-b border-l",
          "bottom-4 right-4 border-b border-r",
        ].map((cls, i) => (
          <motion.div
            key={i}
            className={`absolute w-5 h-5 ${cls} border-accent-soft`}
            animate={{ opacity: active ? [1, 0.5, 1] : 0.6 }}
            transition={{ duration: 0.8, repeat: Infinity }}
          />
        ))}

        {/* Status bar */}
        <div className="absolute bottom-4 inset-x-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <motion.div
              className="w-2 h-2 rounded-full bg-success"
              animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            />
            <span className="text-xs text-text-muted font-mono">
              {active ? "SCANNING…" : "READY"}
            </span>
          </div>
          <span className="text-xs text-text-subtle font-mono">v2.4.1</span>
        </div>

        {/* Identity chip */}
        <motion.div
          className="absolute top-4 inset-x-4 flex items-center justify-between"
          animate={{ opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 3, repeat: Infinity }}
        >
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-accent-violet/30 border border-accent-violet/40 flex items-center justify-center">
              <Scan className="w-3 h-3 text-accent-soft" />
            </div>
            <span className="text-xs font-semibold text-text-secondary">BioID</span>
          </div>
          <Wifi className="w-3.5 h-3.5 text-success" />
        </motion.div>
      </div>

      {/* Orbiting dot */}
      <motion.div
        className="absolute w-3 h-3 rounded-full bg-accent-violet shadow-glow-sm"
        animate={{
          x: [140, 0, -140, 0, 140],
          y: [0, -140, 0, 140, 0],
          opacity: [1, 0.6, 1, 0.6, 1],
        }}
        transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
      />
    </div>
  );
}
