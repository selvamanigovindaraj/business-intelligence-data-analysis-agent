import { useChat } from "../hooks/useChat";
import { InputBar } from "./InputBar";
import { MessageBubble } from "./MessageBubble";
import { SourceCitations } from "./SourceCitations";

export function ChatWindow(): JSX.Element {
  // TODO: get sessionId from context/URL
  const { messages, sources, loading, send } = useChat("default-session");

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {sources.length > 0 && <SourceCitations sources={sources} />}
      </div>
      <InputBar onSend={send} disabled={loading} />
    </div>
  );
}
