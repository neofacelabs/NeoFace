"use client";
import { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Float, QuadraticBezierLine } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";
import * as THREE from "three";
import { motion, AnimatePresence } from "framer-motion";

/* ── Node Component (Glassmorphism Panel) ────────────────────────────────── */
interface NodeProps {
  position: [number, number, number];
  title: string;
  subtitle: string;
  icon: React.ReactNode;
  status?: "pending" | "scanning" | "verified";
  color: string;
  delay?: number;
}

function WorkflowNode({ position, title, subtitle, icon, status = "verified", color, delay = 0 }: NodeProps) {
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  return (
    <Float floatIntensity={1.5} rotationIntensity={0.2} speed={2}>
      <mesh position={position}>
        <Html transform center distanceFactor={5} zIndexRange={[100, 0]}>
          <AnimatePresence>
            {mounted && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                className="relative overflow-hidden rounded-xl border p-4 w-[240px]"
                style={{
                  background: "rgba(5, 5, 5, 0.45)",
                  backdropFilter: "blur(16px)",
                  WebkitBackdropFilter: "blur(16px)",
                  borderColor: "rgba(255, 255, 255, 0.08)",
                  boxShadow: `0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px inset ${color}20`,
                }}
              >
                {/* Status Glow */}
                <div 
                  className="absolute -top-10 -right-10 w-24 h-24 rounded-full blur-[24px] pointer-events-none"
                  style={{ background: color, opacity: 0.15 }}
                />

                <div className="flex items-start gap-3">
                  <div 
                    className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                    style={{ background: `${color}15`, color: color, border: `1px solid ${color}30` }}
                  >
                    {icon}
                  </div>
                  <div>
                    <div className="text-[14px] font-semibold text-white tracking-tight leading-tight mb-1">
                      {title}
                    </div>
                    <div className="text-[11px] font-mono text-[rgba(255,255,255,0.4)] leading-tight">
                      {subtitle}
                    </div>
                  </div>
                </div>

                {/* Progress bar / Scanning animation */}
                <div className="mt-4 h-[2px] w-full bg-white/5 rounded-full overflow-hidden relative">
                  {status === "scanning" ? (
                    <motion.div
                      className="absolute inset-y-0 left-0"
                      style={{ background: color, width: "30%" }}
                      animate={{ left: ["-30%", "100%"] }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    />
                  ) : status === "verified" ? (
                    <div className="absolute inset-y-0 left-0 w-full" style={{ background: color, opacity: 0.8 }} />
                  ) : null}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Html>
      </mesh>
    </Float>
  );
}

/* ── Connection Lines ────────────────────────────────────────────────────── */
function Connection({ start, end, color = "#00E5A8", active = true }: { start: [number,number,number], end: [number,number,number], color?: string, active?: boolean }) {
  const lineRef = useRef<any>(null);

  useFrame(({ clock }) => {
    if (lineRef.current && active) {
      lineRef.current.material.dashOffset -= 0.01;
    }
  });

  return (
    <QuadraticBezierLine
      ref={lineRef}
      start={start}
      end={end}
      mid={[ (start[0] + end[0]) / 2, Math.max(start[1], end[1]) + 0.5, (start[2] + end[2]) / 2 ]}
      color={color}
      lineWidth={1.5}
      transparent
      opacity={active ? 0.6 : 0.1}
      dashed={active}
      dashScale={20}
      dashSize={0.5}
      dashOffset={0}
    />
  );
}

/* ── Nodes Configuration ─────────────────────────────────────────────────── */
const ICONS = {
  face: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <path d="M4 8V6a2 2 0 012-2h2M4 16v2a2 2 0 002 2h2M16 4h2a2 2 0 012 2v2M16 20h2a2 2 0 002-2v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5"/>
    </svg>
  ),
  liveness: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  fingerprint: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <path d="M12 2v20M17 5c0 4-2 6-5 6s-5-2-5-6M20 9c0 6-3 9-8 9s-8-3-8-9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  iris: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5"/>
      <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 2"/>
      <circle cx="12" cy="12" r="1" fill="currentColor"/>
    </svg>
  ),
  engine: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M8 12h8M12 8v8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  ),
  success: (
    <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
      <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
};

const NODES_DATA = [
  { id: "face",     pos: [-2.0,  1.6, -1.0], title: "Face Match",      sub: "Score: 0.998", color: "#00E5A8", icon: ICONS.face, status: "verified" as const, delay: 200 },
  { id: "liveness", pos: [-1.6,  0.4,  0.5], title: "Liveness Check",  sub: "Spoof: 0.001", color: "#00D4FF", icon: ICONS.liveness, status: "verified" as const, delay: 600 },
  { id: "iris",     pos: [ 1.6,  1.8, -0.5], title: "Iris Scan",       sub: "Match: 0.995", color: "#00E5A8", icon: ICONS.iris, status: "verified" as const, delay: 400 },
  { id: "finger",   pos: [ 1.8,  0.2,  1.0], title: "Fingerprint",     sub: "Vector: Match",color: "#36FFC9", icon: ICONS.fingerprint, status: "verified" as const, delay: 800 },
  { id: "engine",   pos: [ 0.0, -1.0,  0.0], title: "Identity Engine", sub: "Risk: LOW",    color: "#14B8A6", icon: ICONS.engine, status: "scanning" as const, delay: 1200 },
  { id: "granted",  pos: [ 0.0, -2.2,  1.5], title: "Access Granted",  sub: "Token Issued", color: "#A7FFF1", icon: ICONS.success, status: "verified" as const, delay: 2000 },
] as const;

/* ── Scene Assembly ──────────────────────────────────────────────────────── */
function PipelineScene() {
  const { camera } = useThree();
  const mouse = useRef({ x: 0, y: 0 });

  // Mouse parallax
  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      mouse.current.x = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.current.y = -(e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", handleMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMove);
  }, []);

  useFrame(({ clock }) => {
    // Parallax camera movement
    camera.position.x += (mouse.current.x * 1.5 - camera.position.x) * 0.02;
    camera.position.y += (mouse.current.y * 1.5 - camera.position.y) * 0.02;
    camera.lookAt(0, 0, 0);
  });

  return (
    <group>
      {/* Nodes */}
      {NODES_DATA.map(n => (
        <WorkflowNode
          key={n.id}
          position={n.pos as [number,number,number]}
          title={n.title}
          subtitle={n.sub}
          icon={n.icon}
          color={n.color}
          status={n.status}
          delay={n.delay}
        />
      ))}

      {/* Connections into Engine */}
      <Connection start={NODES_DATA[0].pos as any} end={NODES_DATA[4].pos as any} color="#00E5A8" />
      <Connection start={NODES_DATA[1].pos as any} end={NODES_DATA[4].pos as any} color="#00D4FF" />
      <Connection start={NODES_DATA[2].pos as any} end={NODES_DATA[4].pos as any} color="#00E5A8" />
      <Connection start={NODES_DATA[3].pos as any} end={NODES_DATA[4].pos as any} color="#36FFC9" />
      
      {/* Connection out of Engine to Granted */}
      <Connection start={NODES_DATA[4].pos as any} end={NODES_DATA[5].pos as any} color="#A7FFF1" />

      {/* Ambient background particles */}
      <ambientLight intensity={0.5} />
    </group>
  );
}

/* ── Main Export ─────────────────────────────────────────────────────────── */
export default function BiometricWorkflow() {
  return (
    <div className="w-full h-full min-h-[600px] relative">
      <Canvas
        camera={{ position: [0, 0, 8], fov: 45 }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <PipelineScene />
        
        <EffectComposer>
          <Bloom 
            intensity={1.2} 
            luminanceThreshold={0.2} 
            luminanceSmoothing={0.9} 
            blendFunction={BlendFunction.SCREEN}
          />
        </EffectComposer>
      </Canvas>
      
      {/* Gradient overlay to blend with background */}
      <div 
        className="absolute inset-0 pointer-events-none" 
        style={{
          background: "radial-gradient(circle at 50% 50%, transparent 40%, rgba(0,0,0,0.8) 100%)"
        }}
      />
    </div>
  );
}
