import { FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

const CATS = ["GARBAGE", "ROADS", "STREETLIGHTS", "WATER_LEAKAGE", "DRAINAGE", "SANITATION", "PUBLIC_PROPERTY", "ELECTRICITY", "HEALTH", "OTHER"];
const STATUSES = ["SUBMITTED", "UNDER_REVIEW", "ASSIGNED", "IN_PROGRESS", "ON_HOLD", "RESOLVED", "REOPENED", "CLOSED", "REJECTED"];

export function ComplaintNewPage() {
  const nav = useNavigate();
  const { can } = useAuth();
  const [error, setError] = useState("");
  const [gpsMsg, setGpsMsg] = useState("Location not captured. CivicLink will ask before storing GPS.");
  const [form, setForm] = useState({
    title: "",
    description: "",
    category: "ROADS",
    latitude: null as number | null,
    longitude: null as number | null,
    location_permission_granted: false,
    location_adjusted: false,
    address_text: "",
  });
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  async function captureGps() {
    if (!navigator.geolocation) {
      setGpsMsg("Geolocation is not supported on this device.");
      return;
    }
    setGpsMsg("Requesting location permission…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((f) => ({
          ...f,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          location_permission_granted: true,
        }));
        setGpsMsg(`Location captured at ${new Date().toLocaleString()}. You may adjust the pin if GPS is inaccurate.`);
      },
      () => setGpsMsg("Location permission denied. You can still submit without GPS, or type an address."),
    );
  }

  async function startCamera(video: boolean) {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: true, audio: video });
      setStream(s);
      if (videoRef.current) videoRef.current.srcObject = s;
    } catch {
      setError("Camera permission denied or unavailable.");
    }
  }

  async function snapshot(complaintId: string, source: string) {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/jpeg", 0.85));
    if (!blob) return;
    const fd = new FormData();
    fd.append("file", blob, "capture.jpg");
    fd.append("source", source);
    if (form.latitude != null) fd.append("gps_lat", String(form.latitude));
    if (form.longitude != null) fd.append("gps_lng", String(form.longitude));
    fd.append("captured_at", new Date().toISOString());
    const r = await api<{ verificationStatus: string; message?: string }>(`/api/v1/complaints/${complaintId}/evidence`, {
      method: "POST",
      body: fd,
    });
    if (r.message) alert(r.message);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!can("COMPLAINT", "CREATE")) {
      setError("You cannot create complaints.");
      return;
    }
    setError("");
    try {
      const c = await api<{ id: string }>("/api/v1/complaints", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          location_captured_at: form.location_permission_granted ? new Date().toISOString() : null,
        }),
      });
      if (stream) await snapshot(c.id, "CAMERA_CAPTURE");
      nav(`/app/complaints/${c.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submit failed");
    }
  }

  return (
    <form onSubmit={onSubmit} className="max-w-2xl space-y-4">
      <h1 className="font-display text-2xl">Submit complaint</h1>
      <label className="block text-sm">Title
        <input className="mt-1 w-full glass rounded-xl px-3 py-2 bg-transparent" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required minLength={4} />
      </label>
      <label className="block text-sm">Category
        <select className="mt-1 w-full glass rounded-xl px-3 py-2 bg-civic-950" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          {CATS.map((c) => <option key={c}>{c}</option>)}
        </select>
      </label>
      <label className="block text-sm">Description
        <textarea className="mt-1 w-full glass rounded-xl px-3 py-2 bg-transparent min-h-28" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required minLength={10} />
      </label>
      <div className="glass rounded-xl p-4 space-y-2">
        <p className="text-sm">{gpsMsg}</p>
        <button type="button" className="rounded-lg bg-cyan-500/20 px-3 py-1 text-sm" onClick={captureGps}>Use current location</button>
        {form.latitude != null && (
          <p className="text-xs text-slate-400">{form.latitude.toFixed(5)}, {form.longitude?.toFixed(5)}
            <button type="button" className="ml-2 underline" onClick={() => setForm({ ...form, location_adjusted: true, latitude: form.latitude! + 0.0001 })}>Nudge pin</button>
          </p>
        )}
      </div>
      <div className="glass rounded-xl p-4 space-y-2">
        <p className="text-sm">Evidence — camera capture is marked CAMERA_CAPTURE. Uploads are UPLOADED_FILE.</p>
        <div className="flex gap-2">
          <button type="button" className="rounded-lg bg-cyan-500/20 px-3 py-1 text-sm" onClick={() => startCamera(false)}>Capture Photo</button>
          <button type="button" className="rounded-lg bg-cyan-500/20 px-3 py-1 text-sm" onClick={() => startCamera(true)}>Record Video</button>
        </div>
        <video ref={videoRef} autoPlay muted playsInline className="rounded-lg max-h-48 bg-black w-full" />
      </div>
      {error && <p className="text-red-300" role="alert">{error}</p>}
      <button className="rounded-xl bg-cyan-500 text-civic-950 font-semibold px-5 py-2">Submit</button>
    </form>
  );
}

export function ComplaintsListPage() {
  const [items, setItems] = useState<{ id: string; publicId: string; title: string; status: string; isDemo: boolean }[]>([]);
  const { can } = useAuth();
  useEffect(() => {
    api<{ items: typeof items }>("/api/v1/complaints").then((r) => setItems(r.items)).catch(() => setItems([]));
  }, []);
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h1 className="font-display text-2xl">Complaints</h1>
        {can("COMPLAINT", "CREATE") && <Link className="rounded-xl bg-cyan-500 text-civic-950 px-4 py-2 text-sm font-semibold" to="/app/complaints/new">+ Submit</Link>}
      </div>
      <div className="space-y-2">
        {items.map((c) => (
          <Link key={c.id} to={`/app/complaints/${c.id}`} className="block glass rounded-xl p-4">
            <div className="flex justify-between">
              <span className="font-medium">{c.title}</span>
              <span className="text-cyan-300 text-sm">{c.status}</span>
            </div>
            <div className="text-xs text-slate-400">{c.publicId} {c.isDemo && <span className="text-amber-300">DEMO DATA</span>}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function ComplaintDetailPage() {
  const { id } = useParams();
  const { user, can } = useAuth();
  const [data, setData] = useState<any>(null);
  const [status, setStatus] = useState("IN_PROGRESS");
  useEffect(() => {
    api(`/api/v1/complaints/${id}`).then(setData);
  }, [id]);
  if (!data) return <p>Loading…</p>;
  const c = data.complaint;
  return (
    <div className="space-y-4">
      <h1 className="font-display text-2xl">{c.title}</h1>
      {c.isDemo && <p className="text-amber-300 text-sm">DEMO DATA</p>}
      <p className="text-slate-300">{c.description}</p>
      <ol className="border-l border-cyan-700 pl-4 space-y-2">
        {data.timeline.map((t: any, i: number) => (
          <li key={i}><span className="text-cyan-300">{t.to}</span> <span className="text-xs text-slate-500">{t.at}</span></li>
        ))}
      </ol>
      {data.evidence.map((e: any) => (
        <div key={e.id} className="glass rounded-xl p-3 text-sm">
          {e.verificationStatus} — {e.verificationNotes}
          {(e.verificationStatus === "SUSPICIOUS" || e.verificationStatus === "NEEDS_REVIEW") && (
            <p className="text-amber-300">Evidence requires administrative review.</p>
          )}
        </div>
      ))}
      {can("COMPLAINT", "UPDATE") && (
        <div className="flex gap-2">
          <select className="glass rounded-xl px-2 bg-civic-950" value={status} onChange={(e) => setStatus(e.target.value)}>
            {STATUSES.map((s) => <option key={s}>{s}</option>)}
          </select>
          <button
            className="rounded-xl bg-cyan-500/30 px-3"
            onClick={() => api(`/api/v1/complaints/${id}/status`, { method: "PATCH", body: JSON.stringify({ status, note: `Updated by ${user?.role}` }) }).then(() => api(`/api/v1/complaints/${id}`).then(setData))}
          >
            Update status
          </button>
        </div>
      )}
    </div>
  );
}
