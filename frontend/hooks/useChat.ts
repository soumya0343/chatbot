"use client";

import { useState, useRef, useCallback } from "react";
import { Message, streamChat } from "@/lib/api";

export function useChat(sessionId: string, initialMessages: Message[] = []) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    (userMessage: string, provider: string, model: string) => {
      if (streaming) return;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        session_id: sessionId,
        role: "user",
        content: userMessage,
        sequence_num: messages.length,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setStreaming(true);
      setStreamText("");
      setError(null);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      streamChat(
        sessionId,
        userMessage,
        provider,
        model,
        ctrl.signal,
        (chunk) => setStreamText((t) => t + chunk),
        () => {
          setStreaming(false);
          setStreamText((text) => {
            if (text) {
              setMessages((prev) => [
                ...prev,
                {
                  id: crypto.randomUUID(),
                  session_id: sessionId,
                  role: "assistant",
                  content: text,
                  sequence_num: prev.length,
                  created_at: new Date().toISOString(),
                },
              ]);
            }
            return "";
          });
          abortRef.current = null;
        },
        (err) => {
          setError(err);
          setStreaming(false);
          setStreamText("");
          abortRef.current = null;
        },
      );
    },
    [sessionId, messages.length, streaming],
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, streaming, streamText, error, send, cancel };
}
