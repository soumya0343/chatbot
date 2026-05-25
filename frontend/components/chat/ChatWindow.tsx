"use client";

import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble, StreamingBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import { ProviderSelector } from "./ProviderSelector";
import { useChat } from "@/hooks/useChat";
import { Message } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

interface Props {
  sessionId: string;
  initialMessages: Message[];
  defaultProvider?: string;
  defaultModel?: string;
}

export function ChatWindow({
  sessionId,
  initialMessages,
  defaultProvider = "gemini",
  defaultModel = "gemini-1.5-flash",
}: Props) {
  const [provider, setProvider] = useState(defaultProvider);
  const [model, setModel] = useState(defaultModel);
  const { messages, streaming, streamText, error, send, cancel } = useChat(
    sessionId,
    initialMessages,
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamText]);

  function handleSend(text: string) {
    send(text, provider, model);
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 px-4 py-3 border-b bg-background/95 backdrop-blur">
        <ProviderSelector
          provider={provider}
          model={model}
          onProviderChange={setProvider}
          onModelChange={setModel}
          disabled={streaming}
        />
        {streaming && (
          <Badge variant="secondary" className="animate-pulse">
            Streaming…
          </Badge>
        )}
      </div>

      <ScrollArea className="flex-1 px-4 py-4">
        <div className="space-y-3 max-w-3xl mx-auto">
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          {streaming && streamText && <StreamingBubble text={streamText} />}
          {error && (
            <div className="text-sm text-destructive px-2">{error}</div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="px-4 py-3 border-t bg-background max-w-3xl mx-auto w-full">
        <MessageInput
          onSend={handleSend}
          onCancel={cancel}
          streaming={streaming}
        />
      </div>
    </div>
  );
}
