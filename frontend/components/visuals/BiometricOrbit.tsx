"use client";
import { motion } from "framer-motion";

interface OrbitItem {
  icon: string;
  label: string;
  color: string;
  delay: number;
  radius: number;
  duration: number;
  angle: number;
}

const ITEMS: OrbitItem[] = [
  { icon: "👁", label: "Iris",        color: "#a5b4fc", delay: 0,   radius: 172, duration: 18, angle: 0   },
  { icon: "🔐", label: "Auth",        color: "#34d399", delay: 0.5, radius: 148, duration: 22, angle: 120 },
  { icon: "🧬", label: "Biometrics",  color: "#fbbf24", delay: 1,   radius: 192, duration: 28, angle: 240 },
  { icon: "🛡", label: "Security",   color: "#f87171", delay: 1.5, radius: 160, duration: 20, angle: 60  },
  { icon: "📡", label: "API",         color: "#67e8f9", delay: 2,   radius: 182, duration: 25, angle: 300 },
];

export function BiometricOrbit() {
  return (
    <div className="relative w-[420px] h-[420px] shrink-0">
      {/* Orbit rings */}
      {[148, 172, 192].map((r, i) => (
        <div
          key={i}
          className="absolute rounded-full border border-[rgba(255,255,255,0.04)] top-1/2 left-1/2"
          style={{
            width: r * 2,
            height: r * 2,
            marginLeft: -r,
            marginTop: -r,
          }}
        />
      ))}

      {/* Center face indicator */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
        <div className="relative w-[100px] h-[100px] rounded-full border border-[rgba(124,124,255,0.25)] bg-[rgba(124,124,255,0.06)] flex items-center justify-center">
          {/* Pulse rings */}
          {[1.3, 1.6, 2.0].map((scale, i) => (
            <div
              key={i}
              className="absolute inset-0 rounded-full border border-[rgba(124,124,255,0.12)]"
              style={{ transform: `scale(${scale})`, opacity: 1 - i * 0.3 }}
            />
          ))}
          <svg width="44" height="44" viewBox="0 0 32 32" fill="none">
            <ellipse cx="16" cy="14" rx="7" ry="8.5" stroke="rgba(165,180,252,0.8)" strokeWidth="1.2" fill="none"/>
            <circle cx="13" cy="12" r="1.2" fill="rgba(165,180,252,0.9)"/>
            <circle cx="19" cy="12" r="1.2" fill="rgba(165,180,252,0.9)"/>
            <line x1="9" y1="15.5" x2="23" y2="15.5" stroke="rgba(124,124,255,0.4)" strokeWidth="0.8"/>
            <path d="M13 19 Q16 21.5 19 19" fill="none" stroke="rgba(165,180,252,0.6)" strokeWidth="1"/>
          </svg>
          <div className="absolute -bottom-6 text-[10px] text-[rgba(255,255,255,0.35)] font-mono whitespace-nowrap">
            LIVE
          </div>
        </div>
      </div>

      {/* Orbiting items */}
      {ITEMS.map((item) => (
        <OrbitDot key={item.label} item={item} />
      ))}

      {/* Status lines connecting center to dots */}
      <svg
        className="absolute inset-0 pointer-events-none"
        width="420"
        height="420"
        viewBox="0 0 420 420"
        style={{ opacity: 0.15 }}
      >
        {ITEMS.map((item, i) => {
          const rad = (item.angle * Math.PI) / 180;
          const x2 = 210 + item.radius * Math.cos(rad);
          const y2 = 210 + item.radius * Math.sin(rad);
          return (
            <line
              key={i}
              x1="210" y1="210"
              x2={x2} y2={y2}
              stroke={item.color}
              strokeWidth="0.7"
              strokeDasharray="3 5"
            />
          );
        })}
      </svg>
    </div>
  );
}

function OrbitDot({ item }: { item: OrbitItem }) {
  return (
    <motion.div
      className="absolute top-1/2 left-1/2"
      animate={{ rotate: 360 }}
      transition={{ duration: item.duration, repeat: Infinity, ease: "linear", delay: item.delay }}
      style={{ width: 0, height: 0 }}
    >
      <motion.div
        style={{
          x: item.radius * Math.cos((item.angle * Math.PI) / 180),
          y: item.radius * Math.sin((item.angle * Math.PI) / 180),
        }}
        animate={{ rotate: -360 }}
        transition={{ duration: item.duration, repeat: Infinity, ease: "linear", delay: item.delay }}
      >
        <div
          className="w-[38px] h-[38px] rounded-xl flex flex-col items-center justify-center gap-0 -translate-x-1/2 -translate-y-1/2 border"
          style={{
            background: `rgba(0,0,0,0.85)`,
            borderColor: `${item.color}30`,
            boxShadow: `0 0 12px ${item.color}20`,
          }}
        >
          <span className="text-sm leading-none">{item.icon}</span>
          <span className="text-[8px] font-medium mt-0.5" style={{ color: item.color }}>{item.label}</span>
        </div>
      </motion.div>
    </motion.div>
  );
}
