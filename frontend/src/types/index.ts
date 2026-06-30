export type Role = "user" | "assistant";

export interface SqlRow {
  [key: string]: unknown;
}

export interface ChatMessage {
  id: string;
  role: Role;
  question?: string;
  answer?: string;
  sql?: string;
  rows?: SqlRow[];
  streaming?: boolean;
}

export interface StreamEvent {
  event: "result" | "done";
  sql?: string;
  rows?: SqlRow[];
  answer?: string;
}
