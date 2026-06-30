import { useEffect, useRef } from "react";
import type { JSX } from "react";
import type { ChatMessage } from "../types";
import { InputBar } from "./InputBar";
import { MessageBubble } from "./MessageBubble";

const SUGGESTED_QUERIES = [
  "Top 5 products by total revenue",
  "Customers with the most orders",
  "Monthly order counts for 1997",
  "Employees ranked by sales amount",
];

function SparkleIcon(): JSX.Element {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-7 h-7 text-violet-400">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
    </svg>
  );
}

function EmptyState({ onSelect }: { onSelect: (q: string) => void }): JSX.Element {
  return (
    <div className="flex flex-col items-center h-full text-center px-8 pt-[12%]">
      <div className="w-14 h-14 rounded-2xl bg-violet-500/10 border border-violet-400/20 flex items-center justify-center mb-5">
        <SparkleIcon />
      </div>
      <h2 className="text-base font-semibold text-slate-100 mb-1.5">
        Ask anything about your data
      </h2>
      <p className="text-sm text-slate-500 mb-7 max-w-xs leading-relaxed">
        I'll write the SQL, run it against Northwind, and explain the results.
      </p>
      <div className="grid grid-cols-2 gap-2 w-full max-w-lg">
        {SUGGESTED_QUERIES.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="group text-left px-4 py-3 bg-slate-800/60 border border-slate-700/60 rounded-xl text-sm text-slate-300 hover:text-slate-100 hover:border-violet-500/40 hover:bg-violet-950/30 transition-all duration-150 flex items-start gap-2.5"
          >
            <span className="mt-0.5 text-violet-500 group-hover:text-violet-400 transition-colors shrink-0">›</span>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

interface Props {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (text: string) => Promise<void>;
}

export function ChatWindow({ messages, loading, onSend }: Props): JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="px-6 py-3.5 border-b border-white/[0.06] flex items-center justify-between shrink-0 bg-[#0f0e17]/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-sm font-semibold text-slate-100 leading-tight">SQL Query Assistant</h1>
            <p className="text-xs text-slate-500 mt-0.5">Natural language · SQL · Results</p>
          </div>
        </div>
        {loading && (
          <div className="flex items-center gap-2 text-xs text-violet-400 bg-violet-500/10 border border-violet-500/20 rounded-full px-3 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            Thinking…
          </div>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <EmptyState onSelect={onSend} />
        ) : (
          <div className="px-6 py-5 space-y-5 max-w-4xl mx-auto">
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input — full width, docked to bottom */}
      <InputBar onSend={onSend} disabled={loading} />
    </div>
  );
}
