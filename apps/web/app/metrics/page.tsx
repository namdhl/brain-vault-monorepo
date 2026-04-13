"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface Metrics {
  items: {
    total: number;
    by_status: Record<string, number>;
    by_type: Record<string, number>;
    by_source: Record<string, number>;
  };
  queue: {
    queued: number;
    processed: number;
    failed: number;
  };
  assets: {
    total: number;
  };
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      {children}
    </section>
  );
}

function BarRow({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: "0.88rem" }}>
        <span>{label}</span>
        <span className="muted">{value} ({pct}%)</span>
      </div>
      <div style={{ background: "#1f2937", borderRadius: 4, height: 8, overflow: "hidden" }}>
        <div style={{ background: color, width: `${pct}%`, height: "100%", borderRadius: 4, transition: "width 0.4s" }} />
      </div>
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  queued: "#9ca3af",
  processing: "#60a5fa",
  processed: "#4ade80",
  failed: "#f87171",
  duplicate: "#a78bfa",
  needs_review: "#fb923c",
  archived: "#a8a29e",
};

const TYPE_COLORS: Record<string, string> = {
  text: "#60a5fa", link: "#34d399", image: "#f59e0b", video: "#f87171", document: "#a78bfa",
};

export default function MetricsPage() {
  const [data, setData] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = () => {
    setLoading(true);
    fetch(`${API_BASE}/v1/metrics`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => { setData(d); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  };

  useEffect(() => { load(); }, []);

  return (
    <main>
      <section className="panel">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1>Metrics</h1>
            <p className="muted">Live operational stats from the API.</p>
          </div>
          <button onClick={load} style={{ width: "auto", padding: "8px 18px" }}>Refresh</button>
        </div>
      </section>

      {loading && <section className="panel"><p className="muted">Loading…</p></section>}
      {error && <section className="panel"><p className="error">{error}</p></section>}

      {data && (
        <>
          {/* Top stat cards */}
          <section className="panel">
            <div className="stat-grid">
              <div className="stat-card">
                <div className="stat-value" style={{ color: "#60a5fa" }}>{data.items.total}</div>
                <div className="stat-label">Total Items</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: "#4ade80" }}>{data.queue.processed}</div>
                <div className="stat-label">Processed Jobs</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: "#9ca3af" }}>{data.queue.queued}</div>
                <div className="stat-label">Queued Jobs</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: "#f87171" }}>{data.queue.failed}</div>
                <div className="stat-label">Failed Jobs</div>
              </div>
              <div className="stat-card">
                <div className="stat-value" style={{ color: "#a78bfa" }}>{data.assets.total}</div>
                <div className="stat-label">Assets</div>
              </div>
            </div>
          </section>

          <Section title="Items by Status">
            {Object.entries(data.items.by_status).map(([s, n]) => (
              <BarRow key={s} label={s} value={n} total={data.items.total} color={STATUS_COLORS[s] ?? "#6b7280"} />
            ))}
          </Section>

          <Section title="Items by Type">
            {Object.entries(data.items.by_type).map(([t, n]) => (
              <BarRow key={t} label={t} value={n} total={data.items.total} color={TYPE_COLORS[t] ?? "#6b7280"} />
            ))}
          </Section>

          <Section title="Items by Source">
            {Object.entries(data.items.by_source).map(([s, n]) => (
              <BarRow key={s} label={s} value={n} total={data.items.total} color="#60a5fa" />
            ))}
          </Section>
        </>
      )}
    </main>
  );
}
