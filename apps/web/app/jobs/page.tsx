"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface Item {
  id: string;
  type: string;
  source: string;
  title?: string;
  status: string;
  created_at: string;
  updated_at: string;
  error_code?: string;
  error_message?: string;
  failed_stage?: string;
  note_path?: string;
}

type StatKey = "queued" | "processing" | "processed" | "failed";

const STAT_COLORS: Record<StatKey, string> = {
  queued: "#9ca3af",
  processing: "#60a5fa",
  processed: "#4ade80",
  failed: "#f87171",
};

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString();
}

export default function JobsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<StatKey>("queued");

  const load = () => {
    setLoading(true);
    fetch(`${API_BASE}/v1/items?limit=200`)
      .then((r) => r.json())
      .then((data) => {
        setItems(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => { load(); }, []);

  const counts: Record<StatKey, number> = {
    queued: items.filter((i) => i.status === "queued").length,
    processing: items.filter((i) => i.status === "processing").length,
    processed: items.filter((i) => i.status === "processed").length,
    failed: items.filter((i) => i.status === "failed").length,
  };

  const visible = items.filter((i) => i.status === activeTab);

  return (
    <main>
      <section className="panel">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1>Jobs Dashboard</h1>
            <p className="muted">Overview of processing pipeline by status.</p>
          </div>
          <button onClick={load} style={{ width: "auto", padding: "8px 18px" }}>
            Refresh
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="stat-grid">
          {(Object.keys(counts) as StatKey[]).map((key) => (
            <div
              key={key}
              className="stat-card"
              style={{ cursor: "pointer", borderColor: activeTab === key ? STAT_COLORS[key] : undefined }}
              onClick={() => setActiveTab(key)}
            >
              <div className="stat-value" style={{ color: STAT_COLORS[key] }}>{counts[key]}</div>
              <div className="stat-label">{key}</div>
            </div>
          ))}
        </div>

        {loading && <p className="muted">Loading…</p>}
        {error && <p className="error">{error}</p>}

        {!loading && !error && (
          <>
            <h2 style={{ marginBottom: 12 }}>
              <StatusBadge status={activeTab} />
              <span style={{ marginLeft: 8 }}>{counts[activeTab]} items</span>
            </h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Title / ID</th>
                    <th>Type</th>
                    <th>Source</th>
                    <th>Updated</th>
                    {activeTab === "failed" && <th>Error</th>}
                    {activeTab === "processed" && <th>Note</th>}
                  </tr>
                </thead>
                <tbody>
                  {visible.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">No items with status "{activeTab}".</td>
                    </tr>
                  )}
                  {visible.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <Link href={`/items/${item.id}`} className="row-link">
                          {item.title || `Untitled ${item.type}`}
                        </Link>
                        <br />
                        <small className="muted">{item.id}</small>
                      </td>
                      <td>{item.type}</td>
                      <td>{item.source}</td>
                      <td><span className="muted">{formatDate(item.updated_at)}</span></td>
                      {activeTab === "failed" && (
                        <td>
                          <span className="muted">
                            {item.error_code || "—"}
                            {item.failed_stage ? ` @ ${item.failed_stage}` : ""}
                          </span>
                        </td>
                      )}
                      {activeTab === "processed" && (
                        <td>
                          {item.note_path
                            ? <code style={{ fontSize: "0.78rem" }}>{item.note_path}</code>
                            : <span className="muted">—</span>}
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
