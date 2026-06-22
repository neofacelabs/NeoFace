"use client";
import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Points, PointMaterial, Trail } from "@react-three/drei";
import * as THREE from "three";

function CoreParticles() {
  const ref = useRef<THREE.Points>(null);
  const count = 3000;
  
  const [positions, sizes] = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const sizes = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * 2 * Math.PI;
      const phi = Math.acos(Math.random() * 2 - 1);
      
      // Face mesh abstract shape (slightly elongated sphere)
      const r = 1.6 + Math.random() * 0.4;
      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta) * 1.2; // elongated vertically
      const z = r * Math.cos(phi) * 0.8; // flattened depth
      
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      
      // sizes[i] = Math.random() * 1.5;
    }
    return [positions, sizes];
  }, []);

  useFrame((state) => {
    if (ref.current) {
      // Base slow rotation
      ref.current.rotation.y = state.clock.elapsedTime * 0.08;
      ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1;

      // React to cursor
      ref.current.rotation.y += (state.pointer.x * 0.2 - ref.current.rotation.y) * 0.05;
      ref.current.rotation.x += (-state.pointer.y * 0.2 - ref.current.rotation.x) * 0.05;
    }
  });

  return (
    <Points ref={ref} positions={positions} stride={3} frustumCulled={false}>
      <PointMaterial 
        transparent 
        color="#00E5A8" 
        size={0.015} 
        sizeAttenuation={true} 
        depthWrite={false} 
        opacity={0.45} 
        blending={THREE.AdditiveBlending}
      />
    </Points>
  );
}

function FingerprintTopology() {
  const ref = useRef<THREE.LineSegments>(null);
  
  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    const points = [];
    // Abstract flowing curves mapping to a sphere
    const numCurves = 40;
    const pointsPerCurve = 50;
    for (let i = 0; i < numCurves; i++) {
      const phi = (i / numCurves) * Math.PI;
      for (let j = 0; j < pointsPerCurve; j++) {
        const theta = (j / pointsPerCurve) * Math.PI * 2;
        const noise = Math.sin(phi * 10) * 0.1;
        const r = 2.1 + noise;
        points.push(
          r * Math.sin(phi) * Math.cos(theta),
          r * Math.cos(phi),
          r * Math.sin(phi) * Math.sin(theta)
        );
      }
    }
    geo.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
    return geo;
  }, []);

  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.y = state.clock.elapsedTime * -0.05 + (state.pointer.x * 0.1);
      ref.current.rotation.z = state.clock.elapsedTime * 0.02 + (-state.pointer.y * 0.1);
    }
  });

  return (
    <lineSegments ref={ref} geometry={geometry}>
      <lineBasicMaterial color="#14F1D9" transparent opacity={0.08} blending={THREE.AdditiveBlending} />
    </lineSegments>
  );
}

function IrisRings() {
  const ref = useRef<THREE.Group>(null);
  
  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.2) * 0.15 + (-state.pointer.y * 0.15);
      ref.current.rotation.y = state.clock.elapsedTime * 0.12 + (state.pointer.x * 0.15);
    }
  });

  return (
    <group ref={ref}>
      {[2.4, 2.6, 2.9, 3.2].map((radius, i) => (
        <mesh key={i} rotation-x={Math.PI / 2}>
          <ringGeometry args={[radius, radius + 0.015, 128]} />
          <meshBasicMaterial 
            color={i % 2 === 0 ? "#0EA5E9" : "#00E5A8"} 
            transparent 
            opacity={0.3 - i * 0.05} 
            side={THREE.DoubleSide} 
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      ))}
    </group>
  );
}

function AuthenticationPathways() {
  return (
    <group>
      <Trail width={0.08} color="#0EA5E9" length={6} decay={1} local={false}>
        <PathParticle radius={2.8} speed={0.6} offset={0} />
      </Trail>
      <Trail width={0.04} color="#00E5A8" length={10} decay={1} local={false}>
        <PathParticle radius={3.1} speed={-0.4} offset={Math.PI} />
      </Trail>
      <Trail width={0.06} color="#14F1D9" length={5} decay={2} local={false}>
        <PathParticle radius={2.5} speed={0.8} offset={Math.PI / 2} axis="y" />
      </Trail>
    </group>
  );
}

function PathParticle({ radius, speed, offset, axis = "x" }: { radius: number; speed: number; offset: number; axis?: "x" | "y" }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (ref.current) {
      const t = state.clock.elapsedTime * speed + offset;
      if (axis === "x") {
        ref.current.position.set(Math.cos(t) * radius, Math.sin(t * 3) * 0.6, Math.sin(t) * radius);
      } else {
        ref.current.position.set(Math.sin(t) * radius, Math.cos(t) * radius, Math.sin(t * 2) * 0.4);
      }
    }
  });
  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.03, 8, 8]} />
      <meshBasicMaterial color="#ffffff" />
    </mesh>
  );
}

export function IdentityCore() {
  return (
    <div className="w-full h-full absolute inset-0 pointer-events-none" style={{ zIndex: 0 }}>
      <Canvas camera={{ position: [0, 0, 7.5], fov: 45 }} dpr={[1, 2]}>
        <ambientLight intensity={0.5} />
        <CoreParticles />
        <FingerprintTopology />
        <IrisRings />
        <AuthenticationPathways />
      </Canvas>
    </div>
  );
}
