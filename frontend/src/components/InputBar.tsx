import { useRef, useState } from "react";
import type { JSX } from "react";

interface Props {
  onSend: (text: string) => Promise<void>;
  disabled?: boolean;
}

export function InputBar({ onSend, disabled }: Props): JSX.Element {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function handleSubmit(e?: React.FormEvent): Promise<void> {
    e?.preventDefault();
    if (!value.trim() || disabled) return;
    const text = value.trim();
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await onSend(text);
  }

  function handleKeyDown(e: React.KeyboardEvent): void {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>): void {
    setValue(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  const canSend = Boolean(value.trim()) && !disabled;

  return (
    <div className="shrink-0 px-6 pb-5 pt-3 border-t border-white/[0.06] bg-[#0f0e17]">
      <div className="max-w-4xl mx-auto">
        <form
          onSubmit={handleSubmit}
          className="flex items-end gap-3 bg-slate-800/50 border border-slate-700/60 rounded-2xl px-4 py-3 focus-within:border-violet-500/50 focus-within:bg-slate-800/70 transition-all duration-200"
        >
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask a business question about the Northwind database…"
            disabled={disabled}
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder-slate-500 resize-none outline-none leading-relaxed min-h-[24px] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!canSend}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-xl bg-violet-600 hover:bg-violet-500 active:bg-violet-700 disabled:opacity-25 disabled:cursor-not-allowed transition-all duration-150"
            aria-label="Send"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M10 17a.75.75 0 01-.75-.75V5.612L5.29 9.77a.75.75 0 01-1.08-1.04l5.25-5.5a.75.75 0 011.08 0l5.25 5.5a.75.75 0 11-1.08 1.04l-3.96-4.158V16.25A.75.75 0 0110 17z" clipRule="evenodd" />
            </svg>
          </button>
        </form>
        <p className="text-xs text-slate-600 mt-2 text-center select-none">
          <kbd className="font-mono">Enter</kbd> to send · <kbd className="font-mono">Shift+Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
}
