"use client";
import { useEffect, useRef } from "react";

/**
 * Animated SVG face-mesh visual — no external 3D deps required.
 * Draws a wireframe face with orbiting scan line and pulsing landmark dots.
 */
export function FaceMeshCanvas({ size = 380 }: { size?: number }) {
  const scanRef = useRef<SVGLineElement>(null);

  // Animate scan line with rAF
  useEffect(() => {
    let raf = 0;
    let t = 0;
    const h = size * 0.82; // scan travel range
    const top = size * 0.09;

    function tick() {
      t += 0.004;
      const y = top + ((Math.sin(t) + 1) / 2) * h;
      if (scanRef.current) {
        scanRef.current.setAttribute("y1", String(y));
        scanRef.current.setAttribute("y2", String(y));
        const alpha = 0.15 + 0.5 * ((Math.sin(t * 2) + 1) / 2);
        scanRef.current.style.opacity = String(alpha);
      }
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [size]);

  const cx = size / 2;
  const cy = size / 2;

  // Landmark grid — stylised face points
  const landmarks = [
    // Forehead
    [cx, cy - 130], [cx - 40, cy - 125], [cx + 40, cy - 125],
    [cx - 70, cy - 110], [cx + 70, cy - 110],
    // Temples
    [cx - 100, cy - 80], [cx + 100, cy - 80],
    [cx - 115, cy - 40], [cx + 115, cy - 40],
    // Eyes
    [cx - 65, cy - 52], [cx - 45, cy - 58], [cx - 25, cy - 52],
    [cx - 45, cy - 42], // left eye centre
    [cx + 25, cy - 52], [cx + 45, cy - 58], [cx + 65, cy - 52],
    [cx + 45, cy - 42], // right eye centre
    // Nose
    [cx, cy - 30], [cx - 15, cy],  [cx + 15, cy],  [cx, cy + 8],
    // Cheeks
    [cx - 90, cy + 10], [cx + 90, cy + 10],
    [cx - 100, cy + 50],[cx + 100, cy + 50],
    // Mouth
    [cx - 45, cy + 50], [cx - 20, cy + 58], [cx, cy + 62],
    [cx + 20, cy + 58], [cx + 45, cy + 50],
    [cx - 30, cy + 80], [cx, cy + 88], [cx + 30, cy + 80],
    // Jaw
    [cx - 85, cy + 90], [cx + 85, cy + 90],
    [cx - 60, cy + 125],[cx + 60, cy + 125],
    [cx, cy + 140],
  ];

  // Edges connecting landmarks
  const edges: [number, number][] = [
    [0,1],[0,2],[1,3],[2,4],[3,5],[4,6],[5,7],[6,8],
    [7,8],[5,9],[6,13],
    [9,10],[10,11],[11,12],[12,9],
    [13,14],[14,15],[15,16],[16,13],
    [0,17],[17,18],[17,19],[18,20],[19,20],
    [7,21],[8,22],[21,23],[22,24],
    [23,25],[25,26],[26,27],[27,28],[28,24],
    [29,30],[30,31],[25,29],[28,31],
    [23,32],[24,33],[32,34],[33,34],
    [34,35],[35,36],
  ];

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="overflow-visible"
    >
      <defs>
        <radialGradient id="fmGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%"   stopColor="rgba(124,124,255,0.18)" />
          <stop offset="100%" stopColor="rgba(124,124,255,0)" />
        </radialGradient>
        <filter id="blur4">
          <feGaussianBlur stdDeviation="4" />
        </filter>
        <linearGradient id="scanGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stopColor="rgba(124,124,255,0)" />
          <stop offset="30%"  stopColor="rgba(124,124,255,0.7)" />
          <stop offset="70%"  stopColor="rgba(165,180,252,0.9)" />
          <stop offset="100%" stopColor="rgba(124,124,255,0)" />
        </linearGradient>
      </defs>

      {/* Background ambient glow */}
      <ellipse cx={cx} cy={cy} rx={size*0.42} ry={size*0.42} fill="url(#fmGlow)" filter="url(#blur4)" />

      {/* Face oval outline */}
      <ellipse
        cx={cx} cy={cy - 8}
        rx={118} ry={148}
        fill="none"
        stroke="rgba(124,124,255,0.18)"
        strokeWidth="1"
      />

      {/* Mesh edges */}
      {edges.map(([a, b], i) => {
        const [ax, ay] = landmarks[a] ?? [0, 0];
        const [bx, by] = landmarks[b] ?? [0, 0];
        return (
          <line
            key={i}
            x1={ax} y1={ay} x2={bx} y2={by}
            stroke="rgba(99,102,241,0.22)"
            strokeWidth="0.7"
          />
        );
      })}

      {/* Landmark dots */}
      {landmarks.map(([lx, ly], i) => (
        <circle
          key={i}
          cx={lx} cy={ly} r={1.6}
          fill="rgba(165,180,252,0.7)"
          className="mesh-pulse"
          style={{ animationDelay: `${(i * 0.07) % 2}s` }}
        />
      ))}

      {/* Eye-box highlights */}
      <rect x={cx-75} y={cy-68} width={60} height={30}
        rx="8" fill="none" stroke="rgba(124,124,255,0.35)" strokeWidth="0.8" />
      <rect x={cx+15} y={cy-68} width={60} height={30}
        rx="8" fill="none" stroke="rgba(124,124,255,0.35)" strokeWidth="0.8" />

      {/* Animated scan line */}
      <line
        ref={scanRef}
        x1={cx - 130} y1={cy} x2={cx + 130} y2={cy}
        stroke="url(#scanGrad)"
        strokeWidth="1.5"
        style={{ opacity: 0 }}
      />
      {/* Scan line bloom */}
      <line
        ref={undefined}
        x1={cx - 130} y1={cy} x2={cx + 130} y2={cy}
        stroke="rgba(165,180,252,0.08)"
        strokeWidth="12"
        filter="url(#blur4)"
      />

      {/* Corner brackets */}
      {[
        { x: cx - 120, y: cy - 148, r: 0 },
        { x: cx + 120, y: cy - 148, r: 90 },
        { x: cx - 120, y: cy + 132, r: 270 },
        { x: cx + 120, y: cy + 132, r: 180 },
      ].map((b, i) => (
        <g key={i} transform={`translate(${b.x},${b.y}) rotate(${b.r})`}>
          <line x1="0" y1="0" x2="18" y2="0" stroke="rgba(165,180,252,0.6)" strokeWidth="1.5" />
          <line x1="0" y1="0" x2="0"  y2="18" stroke="rgba(165,180,252,0.6)" strokeWidth="1.5" />
        </g>
      ))}
    </svg>
  );
}
