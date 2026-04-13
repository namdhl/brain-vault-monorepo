"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ItemStatus = "queued" | "processing" | "processed" | "failed" | "duplicate" | "needs_review" | "archived";

interface Item {
  id: string;
  type: string;
  source: string;
  title?: string;
  tags: string[];
  status: ItemStatus;
  created_at: string;
}

const STATUS_FILTERS: { label: string; value: ItemStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Queued", value: "queued" },
  { label: "Processing", value: "processing" },
  { label: "Processed", value: "processed" },
  { label: "Failed", value: "failed" },
];

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString();
}

export default function ItemsPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<ItemStatus | "all">("all");

  useEffect(() => {
    fetch(`${API_BASE}/v1/items?limit=100`)
      .then((r) => r.json())
      .then((data) => {
        setItems(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const visible = filter === "all" ? items : items.filter((i) => i.status === filter);

  return (
    <main>
      <section className="panel">
        <h1>Items</h1>
        <p className="muted">All captured items. Click a row to view details.</p>
      </section>

      <section className="panel">
        <div className="filter-bar">
          {STATUS_FILTERS.map(({ label, value }) => (
            <button
              key={value}
              className={filter === value ? "filter-btn active" : "filter-btn"}
              onClick={() => setFilter(value as ItemStatus | "all")}
            >
              {label}
            </button>
          ))}
        </div>

        {loading && <p className="muted">Loading…</p>}
        {error && <p className="error">{error}</p>}

        {!loading && !error && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Tags</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">No items found.</td>
                  </tr>
                )}
                {visible.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link href={`/items/${item.id}`} className="row-link">
                        {item.title || <span className="muted">Untitled {item.type}</span>}
                      </Link>
                    </td>
                    <td>{item.type}</td>
                    <td>{item.source}</td>
                    <td><StatusBadge status={item.status} /></td>
                    <td>
                      <span className="muted">{item.tags.join(", ") || "—"}</span>
                    </td>
                    <td>
                      <span className="muted">{formatDate(item.created_at)}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
