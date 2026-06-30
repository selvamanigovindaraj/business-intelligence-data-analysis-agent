import type { JSX } from "react";
import { useChat } from "./hooks/useChat";
import { ChatWindow } from "./components/ChatWindow";
import { Sidebar } from "./components/Sidebar";

export default function App(): JSX.Element {
  const { messages, loading, send } = useChat();

  return (
    <div className="flex h-screen bg-[#0f0e17] text-slate-100 overflow-hidden">
      <Sidebar onSelectExample={send} />
      <main className="flex-1 flex flex-col min-w-0">
        <ChatWindow messages={messages} loading={loading} onSend={send} />
      </main>
    </div>
  );
}
