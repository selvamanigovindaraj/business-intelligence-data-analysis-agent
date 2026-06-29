import { submitFeedback } from "../services/api";
import type { FeedbackRequest } from "../types";

export function useFeedback(sessionId: string) {
  async function giveFeedback(messageId: string, score: 0 | 1): Promise<void> {
    // TODO: implement
    throw new Error("Not implemented");
  }

  return { giveFeedback };
}
