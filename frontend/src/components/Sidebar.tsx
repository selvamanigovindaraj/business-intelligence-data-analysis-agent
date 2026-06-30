import type { JSX } from "react";

const EXAMPLE_QUERIES = [
  "Top 10 customers by revenue",
  "Monthly sales trend this year",
  "Products with low stock",
  "Orders pending shipment",
  "Best-selling categories",
];

interface SidebarProps {
  onSelectExample?: (query: string) => void;
}

export function Sidebar({ onSelectExample }: SidebarProps): JSX.Element {
  return (
    <aside className="w-60 bg-[#15131f] border-r border-white/[0.06] flex flex-col shrink-0">
      {/* Brand */}
      <div className="px-4 py-4 flex items-center gap-2.5 border-b border-white/[0.06]">
        <div className="w-8 h-8 rounded-lg bg-violet-500/20 border border-violet-400/20 flex items-center justify-center shrink-0">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-4 h-4 text-violet-400">
            <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 5.625c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-100 leading-tight">BI Agent</p>
          <p className="text-xs text-slate-500 truncate">Northwind database</p>
        </div>
      </div>

      {/* Example queries */}
      <div className="flex-1 overflow-y-auto px-3 py-4">
        <p className="px-2 mb-2 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">
          Try asking
        </p>
        <nav className="space-y-0.5">
          {EXAMPLE_QUERIES.map((q) => (
            <button
              key={q}
              onClick={() => onSelectExample?.(q)}
              className="w-full text-left px-2 py-2 text-xs text-slate-400 hover:text-slate-100 hover:bg-white/[0.05] rounded-lg transition-colors duration-100 flex items-center gap-2 group"
            >
              <span className="text-slate-600 group-hover:text-violet-400 transition-colors shrink-0">›</span>
              <span className="truncate">{q}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Footer */}
      <div className="px-4 py-3.5 border-t border-white/[0.06]">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
          <p className="text-xs text-slate-500 truncate">DeepSeek · Qdrant · Phoenix</p>
        </div>
      </div>
    </aside>
  );
}
