import { FormEvent, useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export function AdminUsersPage() {
  const [items, setItems] = useState<any[]>([]);
  const [q, setQ] = useState("");
  useEffect(() => {
    api<{ items: any[] }>(`/api/v1/users?q=${encodeURIComponent(q)}`).then((r) => setItems(r.items));
  }, [q]);
  return (
    <div>
      <h1 className="font-display text-2xl mb-4">Users</h1>
      <input className="glass rounded-xl px-3 py-2 mb-4 w-full max-w-md bg-transparent" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
      <table className="w-full text-sm">
        <thead className="text-slate-400 text-left"><tr><th>Name</th><th>Email</th><th>Role</th><th>Demo</th></tr></thead>
        <tbody>
          {items.map((u) => (
            <tr key={u.id} className="border-t border-white/10">
              <td className="py-2">{u.fullName}</td>
              <td>{u.email}</td>
              <td>{u.role}</td>
              <td>{u.isDemo ? "DEMO" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RolesPage() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api<{ items: any[] }>("/api/v1/roles").then((r) => setItems(r.items));
  }, []);
  async function toggle(role: string, module: string, action: string, allowed: boolean, scope: string) {
    await api("/api/v1/roles/permissions", {
      method: "PUT",
      body: JSON.stringify({ role_code: role, module, action, scope, allowed: !allowed }),
    });
    const r = await api<{ items: any[] }>("/api/v1/roles");
    setItems(r.items);
  }
  return (
    <div className="space-y-8">
      <h1 className="font-display text-2xl">Roles & permissions</h1>
      {items.map((role) => (
        <section key={role.code} className="glass rounded-2xl p-4 overflow-auto">
          <h2 className="font-medium mb-2">{role.code}</h2>
          <table className="text-xs w-full">
            <thead><tr className="text-slate-400"><th>Module</th><th>Action</th><th>Scope</th><th>Allowed</th></tr></thead>
            <tbody>
              {role.permissions.map((p: any) => (
                <tr key={p.module + p.action}>
                  <td>{p.module}</td>
                  <td>{p.action}</td>
                  <td>{p.scope}</td>
                  <td>
                    <button className="text-cyan-300" onClick={() => toggle(role.code, p.module, p.action, p.allowed, p.scope)}>
                      {p.allowed ? "✓" : "—"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

export function AuditPage() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api<{ items: any[] }>("/api/v1/audit-logs").then((r) => setItems(r.items));
  }, []);
  return (
    <div>
      <h1 className="font-display text-2xl mb-4">Audit logs</h1>
      <div className="space-y-2 text-sm">
        {items.map((a) => (
          <div key={a.id} className="glass rounded-xl p-3">
            <span className="text-cyan-300">{a.role}</span> {a.action} {a.module} {a.recordId}
            <div className="text-xs text-slate-500">{a.createdAt} · {a.ip}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function MapPage() {
  const [markers, setMarkers] = useState<any[]>([]);
  useEffect(() => {
    api<{ markers: any[] }>("/api/v1/map").then((r) => setMarkers(r.markers));
  }, []);
  return (
    <div>
      <h1 className="font-display text-2xl mb-2">Smart city map</h1>
      <p className="text-sm text-slate-400 mb-4">Provider is configured by MAPS_PROVIDER (default OpenStreetMap tiles). Markers are permission-filtered.</p>
      <ul className="space-y-2">
        {markers.map((m) => (
          <li key={m.type + m.id} className="glass rounded-xl p-3 text-sm">
            <span className="uppercase text-[10px] text-cyan-300 mr-2">{m.type}</span>
            {m.title} ({m.lat}, {m.lng}) — {m.meta}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CreateProjectButton() {
  const { can, user } = useAuth();
  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    await api("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({
        name: fd.get("name"),
        description: fd.get("description"),
        ward_id: user?.assignedWardId,
      }),
    });
  }
  if (!can("PROJECT", "CREATE") || !user?.assignedWardId) return null;
  return (
    <form onSubmit={onSubmit} className="glass rounded-xl p-4 space-y-2 max-w-md mb-4">
      <input name="name" placeholder="Project name" className="w-full bg-transparent" required />
      <input name="description" placeholder="Description" className="w-full bg-transparent" required />
      <button className="rounded-lg bg-cyan-500 text-civic-950 px-3 py-1 text-sm">Add project</button>
    </form>
  );
}
