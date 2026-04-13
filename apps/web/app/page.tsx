import { CaptureForm } from "@/components/capture-form";
import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <section className="panel">
        <h1>Capture</h1>
        <p className="muted">
          Send text, links, images and videos to your knowledge vault.
          The API queues the item and the worker exports a Markdown note into Obsidian.
        </p>
      </section>

      <CaptureForm />

      <section className="panel">
        <h2>Pipeline</h2>
        <ol>
          <li>Submit item from web, desktop or Telegram.</li>
          <li>API stores the raw item and queues a job.</li>
          <li>Worker converts the item to Markdown and writes a note into the vault.</li>
          <li>Later, add MarkItDown and enrichment steps.</li>
        </ol>
        <p style={{ marginTop: 12 }}>
          <Link href="/items" className="row-link">View all items →</Link>
          {"  "}
          <Link href="/jobs" className="row-link" style={{ marginLeft: 16 }}>Jobs dashboard →</Link>
        </p>
      </section>
    </main>
  );
}
