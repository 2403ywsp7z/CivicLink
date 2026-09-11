import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CivicScene } from "../components/CivicScene";
import { dashboardPath, useAuth } from "../lib/auth";

export function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login(identifier, password);
      nav(dashboardPath(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative min-h-[calc(100vh-72px)] flex items-center justify-center px-4">
      <CivicScene />
      <form onSubmit={onSubmit} className="relative z-10 w-full max-w-md glass rounded-2xl p-8 space-y-4">
        <h1 className="font-display text-2xl">Sign in to CivicLink</h1>
        <p className="text-sm text-slate-400">Government roles are assigned by Admin. Citizens register with the CITIZEN role only.</p>
        <label className="block text-sm">
          Email or mobile
          <input className="mt-1 w-full rounded-xl bg-black/30 px-3 py-2" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required autoComplete="username" />
        </label>
        <label className="block text-sm">
          Password
          <input type="password" className="mt-1 w-full rounded-xl bg-black/30 px-3 py-2" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </label>
        {error && <p className="text-red-300 text-sm" role="alert">{error}</p>}
        <button disabled={busy} className="w-full rounded-xl bg-cyan-500 text-civic-950 font-semibold py-2">
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-sm text-slate-400">
          New citizen? <Link className="text-cyan-300" to="/register">Create an account</Link>
        </p>
        <div className="text-xs text-amber-200/90 border border-amber-500/30 rounded-xl p-3">
          <strong>DEMO credentials</strong> (password for all: <code>Demo@CivicLink2026</code>)
          <ul className="mt-1 space-y-0.5">
            <li>citizen@demo.civiclink.local</li>
            <li>nagarsevak@demo.civiclink.local</li>
            <li>officer@demo.civiclink.local</li>
            <li>engineer@demo.civiclink.local</li>
            <li>contractor@demo.civiclink.local</li>
            <li>admin@demo.civiclink.local</li>
          </ul>
        </div>
      </form>
    </div>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [error, setError] = useState("");
  const [form, setForm] = useState({ full_name: "", email: "", mobile: "", password: "", confirm_password: "" });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await register(form);
      nav("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="relative min-h-[calc(100vh-72px)] flex items-center justify-center px-4">
      <CivicScene interactive={false} />
      <form onSubmit={onSubmit} className="relative z-10 w-full max-w-md glass rounded-2xl p-8 space-y-3">
        <h1 className="font-display text-2xl">Citizen registration</h1>
        <p className="text-sm text-slate-400">Role is fixed as CITIZEN. Official accounts are created by Admin.</p>
        {(["full_name", "email", "mobile", "password", "confirm_password"] as const).map((k) => (
          <label key={k} className="block text-sm capitalize">
            {k.replaceAll("_", " ")}
            <input
              type={k.includes("password") ? "password" : "text"}
              className="mt-1 w-full rounded-xl bg-black/30 px-3 py-2"
              value={form[k]}
              onChange={(e) => setForm({ ...form, [k]: e.target.value })}
              required={k !== "mobile"}
            />
          </label>
        ))}
        {error && <p className="text-red-300 text-sm" role="alert">{error}</p>}
        <button className="w-full rounded-xl bg-cyan-500 text-civic-950 font-semibold py-2">Register</button>
      </form>
    </div>
  );
}
