import type { ConversationResponse, FeedbackRequest } from "../types";

const BASE = "/api/v1";

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<ConversationResponse> {
  // TODO: implement
  throw new Error("Not implemented");
}

export async function submitFeedback(feedback: FeedbackRequest): Promise<void> {
  // TODO: implement
  throw new Error("Not implemented");
}

export async function clearSession(sessionId: string): Promise<void> {
  // TODO: implement
  throw new Error("Not implemented");
}
