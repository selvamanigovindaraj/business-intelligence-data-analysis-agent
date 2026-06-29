import { useState } from "react";

interface Props {
  onSend: (text: string) => Promise<void>;
  disabled?: boolean;
}

export function InputBar({ onSend, disabled }: Props): JSX.Element {
  const [value, setValue] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!value.trim()) return;
    await onSend(value.trim());
    setValue("");
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 flex gap-2 border-t border-gray-800">
      <input
        className="flex-1 bg-gray-800 rounded-lg px-4 py-2 text-sm outline-none"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask a business question…"
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="px-4 py-2 bg-blue-600 rounded-lg text-sm disabled:opacity-50"
      >
        Send
      </button>
    </form>
  );
}
