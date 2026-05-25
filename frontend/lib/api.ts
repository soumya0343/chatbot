const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Session {
  id: string;
  title: string | null;
  provider: string;
  model: string;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  total_tokens: number;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sequence_num: number;
  created_at: string;
}

export interface SessionWithMessages extends Session {
  messages: Message[];
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  sessions: {
    list: (): Promise<Session[]> => req("/sessions"),
    get: (id: string): Promise<SessionWithMessages> => req(`/sessions/${id}`),
    create: (provider: string, model: string): Promise<Session> =>
      req("/sessions", {
        method: "POST",
        body: JSON.stringify({ provider, model }),
      }),
    update: (id: string, data: Partial<Pick<Session, "title" | "status">>) =>
      req<Session>(`/sessions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      req<void>(`/sessions/${id}`, { method: "DELETE" }),
  },
};

export function streamChat(
  sessionId: string,
  userMessage: string,
  provider: string,
  model: string,
  signal: AbortSignal,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
): void {
  const url = new URL(`${API_BASE}/sessions/${sessionId}/stream`);
  url.searchParams.set("user_message", userMessage);
  url.searchParams.set("provider", provider);
  url.searchParams.set("model", model);

  const es = new EventSource(url.toString());

  signal.addEventListener("abort", () => {
    es.close();
    onDone();
  });

  es.addEventListener("chunk", (e) => onChunk(e.data));
  es.addEventListener("done", () => {
    es.close();
    onDone();
  });
  es.addEventListener("error", (e) => {
    const msg = (e as MessageEvent).data ?? "Stream error";
    es.close();
    onError(msg);
  });
  es.onerror = () => {
    es.close();
    onDone();
  };
}
