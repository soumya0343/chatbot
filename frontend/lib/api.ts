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

/** Turn a raw provider/SSE error into a short, human-readable message. */
export function humanizeError(raw: string): string {
  if (!raw) return "Something went wrong. Please try again.";
  const lower = raw.toLowerCase();
  if (lower.includes("quota") || lower.includes("429") || lower.includes("rate limit")) {
    return "Rate limit or quota exceeded for this model. Try again shortly, or switch provider/model.";
  }
  if (
    lower.includes("invalid_api_key") ||
    lower.includes("api key") ||
    lower.includes("401") ||
    lower.includes("unauthorized")
  ) {
    return "This provider's API key is missing or invalid.";
  }
  // Pull the embedded "message": "..." if the error is a JSON-ish blob.
  const m = raw.match(/['"]message['"]\s*:\s*["']([^"']+)["']/);
  let msg = m ? m[1] : raw;
  if (msg.length > 240) msg = msg.slice(0, 240) + "…";
  return msg;
}

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
  let finished = false;

  const finish = (cb: () => void) => {
    if (finished) return;
    finished = true;
    es.close();
    cb();
  };

  signal.addEventListener("abort", () => finish(onDone));

  // The api emits default ("message") SSE events carrying a JSON payload whose
  // `type` field is chunk | done | error (plus a literal "[DONE]" sentinel).
  es.onmessage = (e) => {
    if (e.data === "[DONE]") {
      finish(onDone);
      return;
    }
    let msg: { type?: string; text?: string; error?: string };
    try {
      msg = JSON.parse(e.data);
    } catch {
      return;
    }
    if (msg.type === "chunk") {
      onChunk(msg.text ?? "");
    } else if (msg.type === "done") {
      finish(onDone);
    } else if (msg.type === "error") {
      finish(() => onError(humanizeError(msg.error ?? "")));
    }
  };

  // Native connection error (network/cold start). If the stream already
  // finished cleanly this won't double-fire thanks to the `finished` guard.
  es.onerror = () => {
    finish(() => onError("Connection lost"));
  };
}
