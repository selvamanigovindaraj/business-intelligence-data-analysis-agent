import { useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { streamQuestion } from "../services/api";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(0);

  async function send(text: string): Promise<void> {
    const uid = String(++idRef.current);
    const aid = String(++idRef.current);

    setMessages((prev) => [
      ...prev,
      { id: uid, role: "user", question: text },
      { id: aid, role: "assistant", streaming: true },
    ]);
    setLoading(true);
    setError(null);

    try {
      await streamQuestion(text, (ev) => {
        if (ev.event === "result") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aid
                ? { ...m, answer: ev.answer, sql: ev.sql, rows: ev.rows }
                : m
            )
          );
        }
        if (ev.event === "done") {
          setMessages((prev) =>
            prev.map((m) => (m.id === aid ? { ...m, streaming: false } : m))
          );
        }
      });
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aid
            ? {
                ...m,
                answer: "Request failed. Please check the backend and try again.",
                streaming: false,
              }
            : m
        )
      );
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return { messages, loading, error, send };
}
