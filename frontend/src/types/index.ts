export type Role = "user" | "assistant" | "system";

export interface Message {
  id: string;
  role: Role;
  content: string;
  created_at: string;
}

export interface SourceDocument {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
  score?: number;
}

export interface ConversationResponse {
  session_id: string;
  message: Message;
  sources: SourceDocument[];
  cost_usd?: number;
}

export interface FeedbackRequest {
  session_id: string;
  message_id: string;
  score: 0 | 1;
  comment?: string;
}
