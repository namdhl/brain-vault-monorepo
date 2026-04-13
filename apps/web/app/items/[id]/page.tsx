"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface ItemDetail {
  id: string;
  type: string;
  source: string;
  title?: string;
  content?: string;
  original_url?: string;
  tags: string[];
  status: string;
  created_at: string;
  updated_at: string;
  processed_at?: string;
  note_path?: string;
  summary?: string;
  language?: string;
  error_code?: string;
  error_message?: string;
  failed_stage?: string;
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value) return null;
  return (
    <>
      <dt className="detail-label">{label}</dt>
      <dd style={{ margin: 0 }}>{value}</dd>
    </>
  );
}

export default function ItemDetailPage({ params }: { params: { id: string } }) {
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/v1/items/${params.id}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setItem(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [params.id]);

  return (
    <main>
      <section className="panel">
        <Link href="/items" className="back-link">← Back to Items</Link>
        {loading && <p className="muted">Loading…</p>}
        {error && <p className="error">{error}</p>}

        {item && (
          <>
            <h1>{item.title || `Untitled ${item.type}`}</h1>
            <StatusBadge status={item.status} />

            <h2 style={{ marginTop: 24 }}>Metadata</h2>
            <dl className="detail-grid">
              <Row label="ID" value={<code>{item.id}</code>} />
              <Row label="Type" value={item.type} />
              <Row label="Source" value={item.source} />
              <Row label="Language" value={item.language} />
              <Row label="Tags" value={item.tags.length ? item.tags.join(", ") : null} />
              <Row label="Created" value={new Date(item.created_at).toLocaleString()} />
              <Row label="Updated" value={new Date(item.updated_at).toLocaleString()} />
              <Row label="Processed" value={item.processed_at ? new Date(item.processed_at).toLocaleString() : null} />
              {item.original_url && (
                <>
                  <dt className="detail-label">URL</dt>
                  <dd style={{ margin: 0 }}>
                    <a href={item.original_url} target="_blank" rel="noopener noreferrer" className="row-link">
                      {item.original_url}
                    </a>
                  </dd>
                </>
              )}
              <Row label="Note path" value={item.note_path ? <code>{item.note_path}</code> : null} />
            </dl>

            {item.summary && (
              <>
                <h2>Summary</h2>
                <p>{item.summary}</p>
              </>
            )}

            {item.content && (
              <>
                <h2>Content</h2>
                <pre className="code-block">{item.content}</pre>
              </>
            )}

            {item.status === "failed" && (
              <>
                <h2>Error Details</h2>
                <div className="panel" style={{ borderColor: "#7f1d1d" }}>
                  <dl className="detail-grid">
                    <Row label="Error code" value={item.error_code} />
                    <Row label="Failed stage" value={item.failed_stage} />
                    <Row label="Message" value={item.error_message} />
                  </dl>
                </div>
              </>
            )}
          </>
        )}
      </section>
    </main>
  );
}
