// Brain Vault shared TypeScript types
// Sync with services/api/app/schemas.py

export type ItemType = "text" | "link" | "image" | "video" | "document";

export type ItemSource = "web" | "pwa" | "windows" | "telegram" | "api";

export type ItemStatus =
  | "queued"
  | "processing"
  | "processed"
  | "failed"
  | "duplicate"
  | "needs_review"
  | "archived";

export interface CreateItemInput {
  type: ItemType;
  source: ItemSource;
  title?: string;
  content?: string;
  original_url?: string;
  tags?: string[];
  // Extended ingest fields
  mime_type?: string;
  language?: string;
  channel_id?: string;
  chat_id?: string;
  source_message_id?: string;
  metadata?: Record<string, unknown>;
}

export interface ItemRecord extends CreateItemInput {
  id: string;
  status: ItemStatus;
  created_at: string;
  updated_at: string;
  note_path?: string | null;
  processed_at?: string | null;
  canonical_hash?: string | null;
  summary?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  failed_stage?: string | null;
  // obsidian-mind profile fields
  description?: string | null;
  capture_type?: string | null;
  vault_profile?: string | null;
  profile_version?: string | null;
}

// ---------------------------------------------------------------------------
// obsidian-mind vault profile types
// ---------------------------------------------------------------------------

export type NoteKind =
  | "capture-text"
  | "capture-link"
  | "capture-image"
  | "capture-video"
  | "telegram-message"
  | "reference"
  | "brain"
  | "work"
  | "thinking"
  | "query-answer";

export interface EntityRef {
  name: string;
  kind: string; // "tool" | "person" | "concept" | "org" | "domain" | "acronym"
}

export interface ClassifierOutput {
  primary_note_type: NoteKind;
  secondary_actions: string[];
  tags: string[];
  entities: EntityRef[];
  suggested_links: string[];
  confidence: number;
}

export interface VaultProfile {
  profile: string;
  upstream_version: string;
  installed_at: string;
  local_extensions_version: string;
}

// ---------------------------------------------------------------------------
// Query / Answer types
// ---------------------------------------------------------------------------

export type NaturalAnswerStyle = "natural-grounded" | "factual" | "brief";

export interface QueryFilters {
  type?: string;
  source?: string;
  tag?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  folder?: string;
}

export interface QueryRequest {
  query: string;
  filters?: QueryFilters;
  limit?: number;
  answer_style?: NaturalAnswerStyle;
}

export interface Citation {
  note_path: string;
  excerpt: string;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  related_notes: string[];
  answer_style: NaturalAnswerStyle;
  fast_path: boolean;
}
