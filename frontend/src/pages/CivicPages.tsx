import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export function OverviewPage() {
  const { user } = useAuth();
  const [a, setA] = useState<any>(null);
  useEffect(() => {
    api("/api/v1/analytics").then(setA).catch(() => setA(null));
  }, []);
  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl">
        {user?.role === "CITIZEN" ? "Citizen dashboard" : user?.role?.replaceAll("_", " ")}
      </h1>
      {user?.assignedWardName && <p className="text-cyan-300">Assigned ward: {user.assignedWardName}</p>}
      {a?.demoData && <p className="text-amber-300 text-sm">DEMO DATA — figures include fictional seed records.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          ["Resolution rate", `${a?.resolutionRate ?? "—"}%`],
          ["Pending", a?.pendingComplaints ?? "—"],
          ["Satisfaction", a?.satisfactionScore ?? "—"],
          ["Filed vs resolved", `${a?.filedVsResolved?.filed ?? 0} / ${a?.filedVsResolved?.resolved ?? 0}`],
        ].map(([k, v]) => (
          <div key={k} className="glass rounded-2xl p-4">
            <div className="text-xs text-slate-400">{k}</div>
            <div className="text-2xl font-display mt-1">{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function GenericList({ path, title, create }: { path: string; title: string; create?: { module: string; action: string; onCreate: () => void } }) {
  const { can } = useAuth();
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    api<{ items: any[] }>(path).then((r) => setItems(r.items || [])).catch(() => setItems([]));
  }, [path]);
  return (
    <div>
      <div className="flex justify-between mb-4">
        <h1 className="font-display text-2xl">{title}</h1>
        {create && can(create.module, create.action) && (
          <button className="rounded-xl bg-cyan-500 text-civic-950 px-4 py-2 text-sm font-semibold" onClick={create.onCreate}>
            + Add
          </button>
        )}
      </div>
      <div className="grid md:grid-cols-2 gap-3">
        {items.map((it) => (
          <article key={it.id} className="glass rounded-2xl p-4">
            <h2 className="font-medium">{it.title || it.name || it.displayName}</h2>
            <p className="text-sm text-slate-400 mt-1 line-clamp-3">{it.description || it.comment || it.information || it.area}</p>
            {it.isDemo && <span className="text-[10px] text-amber-300">DEMO DATA</span>}
            {it.liveDataUnavailable === undefined && it.status && <div className="text-cyan-300 text-xs mt-2">{it.status}</div>}
          </article>
        ))}
      </div>
    </div>
  );
}

export function ReelsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [filter, setFilter] = useState("latest");
  const { can, user } = useAuth();
  useEffect(() => {
    const p = user ? `/api/v1/reels?filter=${filter}` : `/api/v1/reels?filter=${filter}`;
    api<{ items: any[] }>(p).then((r) => setItems(r.items)).catch(() => setItems([]));
  }, [filter, user]);
  return (
    <div>
      <h1 className="font-display text-2xl mb-4">Development Reels</h1>
      <div className="flex gap-2 mb-4">
        {["latest", "trending"].map((f) => (
          <button key={f} className={`px-3 py-1 rounded-lg ${filter === f ? "bg-cyan-500/30" : "glass"}`} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
      </div>
      <div className="flex gap-4 overflow-x-auto pb-4">
        {items.map((r) => (
          <article key={r.id} className="min-w-[240px] max-w-[240px] glass rounded-2xl overflow-hidden">
            <div className="h-80 bg-gradient-to-b from-cyan-900 to-civic-950 flex items-end p-3">
              <div>
                <h2 className="font-medium">{r.title}</h2>
                {r.officialVerified && <span className="text-[10px] text-emerald-300">Official</span>}
                {r.isDemo && <div className="text-[10px] text-amber-300">DEMO DATA — placeholder media</div>}
              </div>
            </div>
            <div className="p-3 text-xs flex justify-between">
              <span>{r.views} views · {r.likes} likes</span>
              {user && (
                <button onClick={() => api(`/api/v1/reels/${r.id}/like`, { method: "POST" })}>Like</button>
              )}
            </div>
            {can("REEL", "DELETE") && (
              <button className="text-xs px-3 pb-3 text-red-300" onClick={() => api(`/api/v1/reels/${r.id}`, { method: "DELETE" }).then(() => setItems(items.filter((i) => i.id !== r.id)))}>
                Delete
              </button>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}

export function EmergencyPage() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api("/api/v1/emergency").then(setData);
  }, []);
  return (
    <div>
      <h1 className="font-display text-2xl mb-2">Emergency services</h1>
      {data?.liveDataUnavailable && <p className="text-amber-300 mb-4">Live data unavailable</p>}
      <div className="grid md:grid-cols-2 gap-3">
        {(data?.items || []).map((e: any) => (
          <article key={e.id} className="glass rounded-2xl p-4">
            <h2>{e.name}</h2>
            <p className="text-sm text-slate-400">{e.information}</p>
            <p className="text-xs mt-2">Availability: {e.availability} {e.isDemo && "· DEMO DATA"}</p>
            {e.phone ? <a className="text-cyan-300 text-sm" href={`tel:${e.phone}`}>Call</a> : <span className="text-xs text-slate-500">No number configured</span>}
          </article>
        ))}
      </div>
    </div>
  );
}

export function DirectoryPage() {
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api("/api/v1/municipal-officials").then(setData);
  }, []);
  return (
    <div>
      <h1 className="font-display text-2xl">Municipal directory</h1>
      <p className="text-sm text-amber-200 my-2">{data?.disclaimer}</p>
      <div className="grid md:grid-cols-2 gap-3">
        {(data?.items || []).map((o: any) => (
          <article key={o.id} className="glass rounded-2xl p-4">
            <h2>{o.displayName}</h2>
            <p className="text-cyan-300 text-sm">{o.designation}</p>
            <p className="text-sm text-slate-400">{o.responsibilities}</p>
            <p className="text-[10px] mt-2">{o.sourceNote}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

export function FeedbackPage() {
  const { can } = useAuth();
  const [items, setItems] = useState<any[]>([]);
  const [comment, setComment] = useState("");
  useEffect(() => {
    api<{ items: any[] }>("/api/v1/feedback").then((r) => setItems(r.items)).catch(() => setItems([]));
  }, []);
  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl">Feedback</h1>
      {can("FEEDBACK", "CREATE") && (
        <form
          className="glass rounded-xl p-4 space-y-2"
          onSubmit={async (e) => {
            e.preventDefault();
            await api("/api/v1/feedback", { method: "POST", body: JSON.stringify({ rating: 5, comment }) });
            const r = await api<{ items: any[] }>("/api/v1/feedback");
            setItems(r.items);
          }}
        >
          <textarea className="w-full bg-transparent" value={comment} onChange={(e) => setComment(e.target.value)} required />
          <button className="rounded-lg bg-cyan-500 text-civic-950 px-3 py-1 text-sm">Send</button>
        </form>
      )}
      {items.map((f) => (
        <article key={f.id} className="glass rounded-xl p-4">
          <div>{"★".repeat(f.rating)}</div>
          <p>{f.comment}</p>
          {f.officialResponse && <p className="text-cyan-200 text-sm mt-2">Official: {f.officialResponse}</p>}
        </article>
      ))}
    </div>
  );
}

export function ProfilePage() {
  const { user } = useAuth();
  return (
    <div className="glass rounded-2xl p-6 max-w-lg">
      <h1 className="font-display text-2xl">Profile</h1>
      <dl className="mt-4 space-y-2 text-sm">
        <div><dt className="text-slate-400">Name</dt><dd>{user?.fullName}</dd></div>
        <div><dt className="text-slate-400">Email</dt><dd>{user?.email}</dd></div>
        <div><dt className="text-slate-400">Role</dt><dd>{user?.role}</dd></div>
      </dl>
    </div>
  );
}

export function AccessDenied() {
  return <div className="p-10">Access denied. You do not have permission for this area.</div>;
}

export function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <h1 className="font-display text-3xl">About CivicLink</h1>
      <p className="mt-4 text-slate-300">
        CivicLink connects citizens and municipal operations: complaints with GPS and evidence, ward-scoped governance, projects,
        development reels, and audited administration. Official directory and emergency numbers must be imported from verified sources.
      </p>
    </div>
  );
}
