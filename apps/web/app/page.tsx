import { CaptureForm } from "@/components/capture-form";

export default function HomePage() {
  return (
    <main>
      <section className="panel">
        <h1>Brain Vault</h1>
        <p className="muted">
          Capture text, links, images and videos. The API will queue the item,
          and the worker will export a Markdown note into the Obsidian vault.
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
      </section>
    </main>
  );
}
