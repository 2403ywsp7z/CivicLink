import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { CivicScene, FallbackGradient } from "../components/CivicScene";
import { useEffect, useState } from "react";

export function LandingPage() {
  const [webgl, setWebgl] = useState(true);
  useEffect(() => {
    try {
      const c = document.createElement("canvas");
      setWebgl(Boolean(c.getContext("webgl") || c.getContext("experimental-webgl")));
    } catch {
      setWebgl(false);
    }
  }, []);

  return (
    <div className="relative min-h-[calc(100vh-72px)] overflow-hidden">
      {webgl ? <CivicScene /> : <FallbackGradient />}
      <div className="relative z-10 mx-auto max-w-5xl px-6 py-20">
        <motion.p initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-cyan-300 text-sm tracking-[0.3em] uppercase">
          Municipal operating system
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="font-display text-4xl md:text-6xl mt-4 leading-tight"
        >
          One platform connecting citizens, wards, departments, and civic services.
        </motion.h1>
        <p className="mt-6 max-w-2xl text-slate-300 text-lg">
          CivicLink is a secure, role-aware Smart City governance system — complaints, projects, development reels, and municipal
          operations in one place.
        </p>
        <div className="mt-10 flex flex-wrap gap-4">
          <Link to="/login" className="rounded-xl bg-cyan-500 text-civic-950 font-semibold px-5 py-3">
            Sign in
          </Link>
          <Link to="/register" className="rounded-xl glass px-5 py-3">
            Register as citizen
          </Link>
          <Link to="/emergency" className="rounded-xl glass px-5 py-3">
            Emergency
          </Link>
        </div>
        <p className="mt-8 text-xs text-amber-200/80">Demo mode uses clearly labeled fictional data. It is not official government information.</p>
      </div>
    </div>
  );
}
