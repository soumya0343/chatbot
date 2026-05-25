import { api } from "@/lib/api";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function ConversationPage({ params }: Props) {
  const { id } = await params;

  let session;
  try {
    session = await api.sessions.get(id);
  } catch {
    notFound();
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b text-xs text-muted-foreground truncate">
        {session.title ?? "Untitled"} · {session.provider}/{session.model}
      </div>
      <div className="flex-1 min-h-0">
        <ChatWindow
          sessionId={id}
          initialMessages={session.messages}
          defaultProvider={session.provider}
          defaultModel={session.model}
        />
      </div>
    </div>
  );
}
