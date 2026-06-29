import { useState } from "react";
import type { Message, SourceDocument } from "../types";
import { sendMessage } from "../services/api";

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sources, setSources] = useState<SourceDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(text: string): Promise<void> {
    // TODO: implement
    throw new Error("Not implemented");
  }

  return { messages, sources, loading, error, send };
}
