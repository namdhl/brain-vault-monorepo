"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface SearchResult {
  id: string;
  type: string;
  source: string;
  title?: string;
  status: string;
  tags: string[];
  created_at: string;
  note_path?: string;
  summary?: string;
  snippet?: string;
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = (query: string, type: string, status: string) => {
    setLoading(true);
    const params = new URLSearchParams({ limit: "50" });
    if (query) params.set("q", query);
    if (type) params.set("type", type);
    if (status) params.set("status", status);

    fetch(`${API_BASE}/v1/search?${params}`)
      .then((r) => r.json())
      .then((data) => {
        setResults(data);
        setSearched(true);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch(q, typeFilter, statusFilter);
    }, 350);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [q, typeFilter, statusFilter]);

  return (
    <main>
      <section className="panel">
        <h1>Search</h1>
        <p className="muted">Search across all captured items by title, content, summary or tags.</p>

        <label style={{ marginBottom: 8 }}>
          Query
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Type to search…"
            autoFocus
          />
        </label>

        <div style={{ display: "flex", gap: 12 }}>
          <label style={{ flex: 1 }}>
            Type
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="">All types</option>
              <option value="text">Text</option>
              <option value="link">Link</option>
              <option value="image">Image</option>
              <option value="video">Video</option>
              <option value="document">Document</option>
            </select>
          </label>
          <label style={{ flex: 1 }}>
            Status
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              <option value="queued">Queued</option>
              <option value="processed">Processed</option>
              <option value="failed">Failed</option>
            </select>
          </label>
        </div>
      </section>

      <section className="panel">
        {loading && <p className="muted">Searching…</p>}
        {!loading && searched && results.length === 0 && (
          <p className="muted">No results found.</p>
        )}
        {results.map((item) => (
          <div key={item.id} style={{ borderBottom: "1px solid #374151", paddingBottom: 16, marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <Link href={`/items/${item.id}`} className="row-link" style={{ fontWeight: 700, fontSize: "1rem" }}>
                {item.title || `Untitled ${item.type}`}
              </Link>
              <StatusBadge status={item.status} />
              <span className="muted" style={{ fontSize: "0.8rem" }}>{item.type} · {item.source}</span>
            </div>
            {item.snippet && (
              <p style={{ margin: "4px 0", fontSize: "0.88rem", color: "#d1d5db" }}>{item.snippet}</p>
            )}
            {item.tags.length > 0 && (
              <p className="muted" style={{ fontSize: "0.8rem", margin: "4px 0" }}>
                {item.tags.map((t) => `#${t}`).join(" ")}
              </p>
            )}
            <p className="muted" style={{ fontSize: "0.78rem", margin: "2px 0" }}>
              {new Date(item.created_at).toLocaleString()}
              {item.note_path && <> · <code style={{ fontSize: "0.75rem" }}>{item.note_path}</code></>}
            </p>
          </div>
        ))}
      </section>
    </main>
  );
}
