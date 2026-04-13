export type ItemType = "text" | "link" | "image" | "video";

export interface CreateItemInput {
  type: ItemType;
  source: "web" | "pwa" | "windows" | "telegram" | "api";
  title?: string;
  content?: string;
  original_url?: string;
  tags?: string[];
}

export interface ItemRecord extends CreateItemInput {
  id: string;
  status: "queued" | "processing" | "processed" | "failed";
  created_at: string;
  updated_at: string;
  note_path?: string | null;
}
