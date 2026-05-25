"use client";

import { useState, useEffect, useCallback } from "react";
import { api, Session } from "@/lib/api";

export function useConversations() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.sessions.list();
      setSessions(data);
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const deleteSession = useCallback(async (id: string) => {
    await api.sessions.delete(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return { sessions, loading, error, reload: load, deleteSession };
}
