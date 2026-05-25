"use client";

import { Message } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap",
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : "bg-muted text-foreground rounded-bl-sm",
        )}
      >
        {message.content}
      </div>
    </div>
  );
}

export function StreamingBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-start">
      <div className="max-w-[75%] rounded-2xl rounded-bl-sm px-4 py-2 text-sm whitespace-pre-wrap bg-muted text-foreground">
        {text}
        <span className="inline-block w-1.5 h-4 ml-0.5 bg-current animate-pulse rounded-sm align-text-bottom" />
      </div>
    </div>
  );
}
