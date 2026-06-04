"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useConversations } from "@/hooks/useConversations";
import { api } from "@/lib/api";
import { ProviderSelector } from "@/components/chat/ProviderSelector";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Trash2, MessageSquarePlus } from "lucide-react";

export default function ConversationsPage() {
  const router = useRouter();
  const { sessions, loading, error, reload, deleteSession } = useConversations();
  const [provider, setProvider] = useState("groq");
  const [model, setModel] = useState("llama-3.3-70b-versatile");
  const [creating, setCreating] = useState(false);

  async function createSession() {
    setCreating(true);
    try {
      const s = await api.sessions.create(provider, model);
      router.push(`/conversations/${s.id}`);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-2xl mx-auto p-6 space-y-6">
        <div className="flex flex-col gap-3">
          <h1 className="text-2xl font-bold">Conversations</h1>
          <div className="flex gap-2 items-center flex-wrap">
            <ProviderSelector
              provider={provider}
              model={model}
              onProviderChange={setProvider}
              onModelChange={setModel}
            />
            <Button onClick={createSession} disabled={creating} className="gap-2">
              <MessageSquarePlus className="w-4 h-4" />
              New Chat
            </Button>
          </div>
        </div>

        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
        {error && <p className="text-sm text-destructive">{error}</p>}

        {!loading && sessions.length === 0 && (
          <p className="text-sm text-muted-foreground">No conversations yet. Start one above.</p>
        )}

        <div className="space-y-2">
          {sessions.map((s) => (
            <Card key={s.id} className="hover:bg-accent/50 transition-colors">
              <CardHeader className="py-3 px-4">
                <div className="flex items-start justify-between gap-2">
                  <Link
                    href={`/conversations/${s.id}`}
                    className="flex-1 min-w-0"
                  >
                    <CardTitle className="text-sm truncate">
                      {s.title ?? "Untitled"}
                    </CardTitle>
                    <CardDescription className="text-xs mt-0.5">
                      {new Date(s.created_at).toLocaleString()} ·{" "}
                      {s.message_count} msgs · {s.total_tokens} tokens
                    </CardDescription>
                  </Link>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant="outline" className="text-xs">
                      {s.provider}/{s.model}
                    </Badge>
                    <Badge
                      variant={s.status === "active" ? "default" : "secondary"}
                      className="text-xs"
                    >
                      {s.status}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="w-7 h-7 text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.preventDefault();
                        deleteSession(s.id);
                      }}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
