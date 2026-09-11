import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import type { Group } from "three";

function Nodes({ mouse }: { mouse: { x: number; y: number } }) {
  const group = useRef<Group>(null);
  const points = useMemo(() => {
    const pts: [number, number, number][] = [];
    for (let i = 0; i < 36; i++) {
      pts.push([(Math.random() - 0.5) * 8, (Math.random() - 0.5) * 4, (Math.random() - 0.5) * 6]);
    }
    return pts;
  }, []);

  useFrame((_, dt) => {
    if (!group.current) return;
    group.current.rotation.y += dt * 0.05;
    group.current.rotation.x = mouse.y * 0.15;
    group.current.rotation.z = mouse.x * 0.08;
  });

  return (
    <group ref={group}>
      {points.map((p, i) => (
        <Float key={i} speed={1.2} rotationIntensity={0.2} floatIntensity={0.4}>
          <mesh position={p}>
            <sphereGeometry args={[0.05, 12, 12]} />
            <meshStandardMaterial color={i % 3 ? "#22d3ee" : "#4ade80"} emissive="#0891b2" emissiveIntensity={0.55} />
          </mesh>
        </Float>
      ))}
    </group>
  );
}

export function CivicScene({ interactive = true }: { interactive?: boolean }) {
  const reduced = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const mouse = useRef({ x: 0, y: 0 });

  if (reduced) {
    return <div className="absolute inset-0 bg-gradient-to-br from-civic-950 via-cyan-950 to-emerald-950" aria-hidden />;
  }

  return (
    <div
      className="absolute inset-0 -z-10"
      aria-hidden
      onPointerMove={(e) => {
        if (!interactive) return;
        mouse.current.x = (e.clientX / window.innerWidth) * 2 - 1;
        mouse.current.y = (e.clientY / window.innerHeight) * 2 - 1;
      }}
    >
      <Canvas camera={{ position: [0, 0, 6], fov: 50 }} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }}>
        <color attach="background" args={["#051822"]} />
        <fog attach="fog" args={["#051822", 8, 18]} />
        <ambientLight intensity={0.4} />
        <pointLight position={[4, 4, 4]} intensity={1.2} color="#22d3ee" />
        <pointLight position={[-4, -2, 2]} intensity={0.6} color="#4ade80" />
        <Nodes mouse={mouse.current} />
        <gridHelper args={[20, 20, "#0e7490", "#083344"]} position={[0, -2.4, 0]} />
      </Canvas>
    </div>
  );
}

export function FallbackGradient() {
  return (
    <div
      className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_rgba(34,211,238,0.18),_transparent_55%),linear-gradient(180deg,#051822,#062c38)]"
      aria-hidden
    />
  );
}
