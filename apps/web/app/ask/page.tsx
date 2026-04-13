"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface Citation {
  note_path: string;
  excerpt: string;
}

interface QueryResponse {
  answer: string;
  citations: Citation[];
  related_notes: string[];
  answer_style: string;
  fast_path: boolean;
}

function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  return (
    <div style={{ borderLeft: "3px solid #4b5563", paddingLeft: 12, marginBottom: 10 }}>
      <p style={{ margin: "0 0 4px", fontSize: "0.78rem", color: "#9ca3af" }}>
        [{index}] <code>{citation.note_path}</code>
      </p>
      {citation.excerpt && (
        <p style={{ margin: 0, fontSize: "0.85rem", color: "#d1d5db" }}>
          {citation.excerpt}
        </p>
      )}
    </div>
  );
}

export default function AskPage() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const filters: Record<string, string> = {};
    if (typeFilter) filters.type = typeFilter;
    if (sourceFilter) filters.source = sourceFilter;
    if (tagFilter) filters.tag = tagFilter;

    try {
      const resp = await fetch(`${API_BASE}/v1/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          filters,
          limit: 10,
          answer_style: "natural-grounded",
        }),
      });

      if (!resp.ok) {
        const msg = await resp.text();
        throw new Error(msg || `HTTP ${resp.status}`);
      }

      const data: QueryResponse = await resp.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <section className="panel">
        <h1>Ask</h1>
        <p className="muted">
          Ask a question about your vault in natural language, or use filter syntax like{" "}
          <code>type:video source:telegram</code>.
        </p>

        <form onSubmit={handleSubmit}>
          <label style={{ marginBottom: 8 }}>
            Query
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. tóm tắt obsidian notes, or type:link source:web"
              autoFocus
            />
          </label>

          <div style={{ display: "flex", gap: 12, marginBottom: 8 }}>
            <label style={{ flex: 1 }}>
              Type
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                <option value="">All types</option>
                <option value="text">Text</option>
                <option value="link">Link</option>
                <option value="image">Image</option>
                <option value="video">Video</option>
              </select>
            </label>
            <label style={{ flex: 1 }}>
              Source
              <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}>
                <option value="">All sources</option>
                <option value="web">Web</option>
                <option value="pwa">PWA</option>
                <option value="telegram">Telegram</option>
                <option value="api">API</option>
              </select>
            </label>
            <label style={{ flex: 1 }}>
              Tag
              <input
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
                placeholder="e.g. obsidian"
              />
            </label>
          </div>

          <button type="submit" disabled={loading || !query.trim()} style={{ marginTop: 4 }}>
            {loading ? "Thinking…" : "Ask"}
          </button>
        </form>
      </section>

      {error && (
        <section className="panel">
          <p style={{ color: "#f87171" }}>Error: {error}</p>
        </section>
      )}

      {result && (
        <>
          <section className="panel">
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <h2 style={{ margin: 0 }}>Answer</h2>
              {result.fast_path && (
                <span
                  className="badge badge-processed"
                  style={{ fontSize: "0.75rem" }}
                  title="Fast path — no LLM synthesis"
                >
                  fast
                </span>
              )}
              {!result.fast_path && (
                <span className="badge badge-queued" style={{ fontSize: "0.75rem" }}>
                  {result.answer_style}
                </span>
              )}
            </div>
            <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: "0.95rem" }}>
              {result.answer}
            </div>
          </section>

          {result.citations.length > 0 && (
            <section className="panel">
              <h2>Citations</h2>
              {result.citations.map((c, i) => (
                <CitationCard key={i} citation={c} index={i + 1} />
              ))}
            </section>
          )}

          {result.related_notes.length > 0 && (
            <section className="panel">
              <h2>Related Notes</h2>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {result.related_notes.map((note, i) => (
                  <li key={i} style={{ fontSize: "0.85rem", color: "#d1d5db", marginBottom: 4 }}>
                    <code>{note}</code>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
