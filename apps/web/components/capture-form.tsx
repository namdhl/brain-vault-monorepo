"use client";

import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function CaptureForm() {
  const [type, setType] = useState("text");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [originalUrl, setOriginalUrl] = useState("");
  const [tags, setTags] = useState("inbox");
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [message, setMessage] = useState("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setState("loading");
    setMessage("");

    const payload = {
      type,
      source: "web",
      title,
      content,
      original_url: originalUrl || undefined,
      tags: tags
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    };

    try {
      const response = await fetch(`${API_BASE}/v1/items`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      const data = await response.json();
      setState("done");
      setMessage(`Queued item ${data.id}. Status: ${data.status}`);
      setTitle("");
      setContent("");
      setOriginalUrl("");
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Unknown error");
    }
  }

  return (
    <section className="panel">
      <h2>Capture</h2>

      <form onSubmit={onSubmit}>
        <label>
          Type
          <select value={type} onChange={(event) => setType(event.target.value)}>
            <option value="text">Text</option>
            <option value="link">Link</option>
            <option value="image">Image</option>
            <option value="video">Video</option>
          </select>
        </label>

        <label>
          Title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Quick note title"
          />
        </label>

        <label>
          Content
          <textarea
            rows={8}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="Paste text, context or a description here"
          />
        </label>

        <label>
          Original URL
          <input
            value={originalUrl}
            onChange={(event) => setOriginalUrl(event.target.value)}
            placeholder="https://example.com"
          />
        </label>

        <label>
          Tags
          <input
            value={tags}
            onChange={(event) => setTags(event.target.value)}
            placeholder="inbox, idea, ai"
          />
        </label>

        <button type="submit" disabled={state === "loading"}>
          {state === "loading" ? "Queuing..." : "Send to server"}
        </button>
      </form>

      {state === "done" && <p className="success">{message}</p>}
      {state === "error" && <p className="error">{message}</p>}
    </section>
  );
}
