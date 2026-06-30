import type { JSX } from "react";
import type { ChatMessage, SqlRow } from "../types";

interface Props {
  message: ChatMessage;
}

function ThinkingDots(): JSX.Element {
  return (
    <div className="flex gap-1.5 items-center py-0.5 px-1">
      <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce [animation-delay:0ms]" />
      <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce [animation-delay:150ms]" />
      <span className="w-2 h-2 rounded-full bg-violet-400 animate-bounce [animation-delay:300ms]" />
    </div>
  );
}

function SectionLabel({ color, label }: { color: string; label: string }): JSX.Element {
  return (
    <div className="flex items-center gap-2 mb-2.5">
      <span className={`w-1.5 h-1.5 rounded-full ${color} shrink-0`} />
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{label}</span>
    </div>
  );
}

function SqlBlock({ sql }: { sql: string }): JSX.Element {
  return (
    <div className="mt-4 pt-4 border-t border-white/[0.06]">
      <SectionLabel color="bg-violet-400" label="Generated SQL" />
      <pre className="bg-slate-950/70 border border-slate-700/40 rounded-xl p-4 text-xs text-violet-300 font-mono overflow-x-auto leading-relaxed whitespace-pre-wrap break-words">
        {sql}
      </pre>
    </div>
  );
}

function ResultsTable({ rows }: { rows: SqlRow[] }): JSX.Element {
  if (rows.length === 0) {
    return (
      <div className="mt-4 pt-4 border-t border-white/[0.06]">
        <SectionLabel color="bg-cyan-400" label="Results" />
        <p className="text-xs text-slate-500 italic">No rows returned.</p>
      </div>
    );
  }

  const columns = Object.keys(rows[0]);
  const display = rows.slice(0, 50);

  return (
    <div className="mt-4 pt-4 border-t border-white/[0.06]">
      <SectionLabel
        color="bg-cyan-400"
        label={`${rows.length} row${rows.length !== 1 ? "s" : ""}${rows.length > 50 ? " · first 50 shown" : ""}`}
      />
      <div className="overflow-x-auto rounded-xl border border-slate-700/40">
        <table className="min-w-full text-xs border-collapse">
          <thead>
            <tr className="bg-slate-800/80 border-b border-slate-700/50">
              {columns.map((col) => (
                <th key={col} className="px-3 py-2.5 text-left text-slate-300 font-semibold whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {display.map((row, i) => (
              <tr
                key={i}
                className={`transition-colors hover:bg-violet-900/10 ${
                  i % 2 === 0 ? "bg-slate-800/40" : "bg-transparent"
                }`}
              >
                {columns.map((col) => (
                  <td
                    key={col}
                    className="px-3 py-2 text-slate-300 whitespace-nowrap max-w-[220px] overflow-hidden text-ellipsis border-b border-slate-700/20 last:border-b-0"
                  >
                    {String(row[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function MessageBubble({ message }: Props): JSX.Element {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-lg px-4 py-2.5 bg-violet-600/20 border border-violet-500/20 rounded-2xl rounded-tr-sm text-sm text-slate-100 leading-relaxed">
          {message.question}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="w-full bg-slate-900/50 border border-white/[0.08] border-l-2 border-l-violet-500/40 rounded-2xl rounded-tl-sm p-4 shadow-sm">
        {message.streaming && !message.answer ? (
          <ThinkingDots />
        ) : (
          <>
            {message.answer && (
              <p className="text-sm text-slate-200 leading-relaxed">{message.answer}</p>
            )}
            {message.sql && <SqlBlock sql={message.sql} />}
            {message.rows !== undefined && <ResultsTable rows={message.rows} />}
          </>
        )}
      </div>
    </div>
  );
}
