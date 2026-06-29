import type { Message } from "../types";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props): JSX.Element {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-prose rounded-xl px-4 py-2 text-sm ${
          isUser ? "bg-blue-600" : "bg-gray-800"
        }`}
      >
        {message.content}
      </div>
    </div>
  );
}
