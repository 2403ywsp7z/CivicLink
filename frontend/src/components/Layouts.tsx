import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Bell, LogOut, Moon, Search, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import { NAV } from "../lib/nav";
import { api } from "../lib/api";

export function AppShell() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [dark, setDark] = useState(true);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ type: string; id: string; title: string; isDemo?: boolean }[]>([]);
  const items = NAV[user?.role || "CITIZEN"] || NAV.CITIZEN;

  useEffect(() => {
    document.documentElement.classList.toggle("light", !dark);
  }, [dark]);

  useEffect(() => {
    if (q.length < 2) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      api<{ items: typeof hits }>(`/api/v1/search?q=${encodeURIComponent(q)}`)
        .then((r) => setHits(r.items))
        .catch(() => setHits([]));
    }, 280);
    return () => clearTimeout(t);
  }, [q]);

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 hidden md:flex flex-col glass m-3 rounded-2xl p-4">
        <div className="font-display text-xl tracking-wide text-cyan-300 mb-6">CivicLink</div>
        <nav className="flex-1 space-y-1" aria-label="Main">
          {items.map((i) => (
            <NavLink
              key={i.to}
              to={i.to}
              className={({ isActive }) =>
                `block rounded-xl px-3 py-2 text-sm ${isActive ? "bg-cyan-500/20 text-cyan-200" : "text-slate-300 hover:bg-white/5"}`
              }
            >
              {i.label}
            </NavLink>
          ))}
        </nav>
        <button
          className="mt-4 flex items-center gap-2 text-sm text-slate-400 hover:text-white"
          onClick={async () => {
            await logout();
            nav("/");
          }}
        >
          <LogOut size={16} /> Logout
        </button>
      </aside>
      <div className="flex-1 min-w-0">
        <header className="flex items-center gap-3 p-4">
          <div className="relative flex-1 max-w-xl">
            <Search className="absolute left-3 top-2.5 text-slate-500" size={16} />
            <input
              aria-label="Global search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search complaints, projects, wards…"
              className="w-full glass rounded-xl pl-9 pr-3 py-2 text-sm bg-transparent"
            />
            {hits.length > 0 && (
              <ul className="absolute z-20 mt-1 w-full glass rounded-xl p-2 text-sm">
                {hits.map((h) => (
                  <li key={h.id} className="px-2 py-1">
                    <span className="text-cyan-300 uppercase text-[10px] mr-2">{h.type}</span>
                    {h.title}
                    {h.isDemo && <span className="ml-2 text-[10px] text-amber-300">DEMO DATA</span>}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button aria-label="Notifications" className="glass rounded-xl p-2">
            <Bell size={16} />
          </button>
          <button aria-label="Toggle theme" className="glass rounded-xl p-2" onClick={() => setDark((d) => !d)}>
            {dark ? <Sun size={16} /> : <Moon size={16} />}
          </button>
          <div className="text-right hidden sm:block">
            <div className="text-sm font-medium">{user?.fullName}</div>
            <div className="text-[11px] text-cyan-400">
              {user?.role}
              {user?.isDemo ? " · DEMO" : ""}
            </div>
          </div>
        </header>
        <main className="p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function PublicLayout() {
  return (
    <div className="min-h-screen">
      <header className="relative z-10 flex flex-wrap items-center justify-between gap-3 px-6 py-4">
        <a href="/" className="font-display text-xl text-cyan-300">
          CivicLink
        </a>
        <nav className="flex flex-wrap gap-4 text-sm text-slate-300" aria-label="Public">
          {NAV.PUBLIC.map((i) => (
            <NavLink key={i.to} to={i.to} className="hover:text-white">
              {i.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <Outlet />
    </div>
  );
}
