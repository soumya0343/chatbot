"use client";

import { useRef, KeyboardEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Send, Square } from "lucide-react";

interface Props {
  onSend: (text: string) => void;
  onCancel: () => void;
  streaming: boolean;
  disabled?: boolean;
}

export function MessageInput({ onSend, onCancel, streaming, disabled }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  function submit() {
    const text = ref.current?.value.trim();
    if (!text || streaming) return;
    ref.current!.value = "";
    onSend(text);
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="flex gap-2 items-end">
      <Textarea
        ref={ref}
        placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
        className="resize-none min-h-[48px] max-h-40"
        onKeyDown={onKey}
        disabled={disabled}
        rows={1}
      />
      {streaming ? (
        <Button
          variant="destructive"
          size="icon"
          onClick={onCancel}
          title="Cancel"
        >
          <Square className="w-4 h-4" />
        </Button>
      ) : (
        <Button size="icon" onClick={submit} disabled={disabled}>
          <Send className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}
