"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PROVIDERS: Record<string, { label: string; models: string[] }> = {
  gemini: {
    label: "Gemini",
    models: ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro"],
  },
  openai: {
    label: "OpenAI",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
  },
  anthropic: {
    label: "Anthropic",
    models: ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-7"],
  },
};

interface Props {
  provider: string;
  model: string;
  onProviderChange: (p: string) => void;
  onModelChange: (m: string) => void;
  disabled?: boolean;
}

export function ProviderSelector({
  provider,
  model,
  onProviderChange,
  onModelChange,
  disabled,
}: Props) {
  const models = PROVIDERS[provider]?.models ?? [];

  function handleProviderChange(p: string | null) {
    if (!p) return;
    onProviderChange(p);
    onModelChange(PROVIDERS[p].models[0]);
  }

  return (
    <div className="flex gap-2">
      <Select value={provider} onValueChange={handleProviderChange} disabled={disabled}>
        <SelectTrigger className="w-36">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(PROVIDERS).map(([k, v]) => (
            <SelectItem key={k} value={k}>
              {v.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={model} onValueChange={(v) => v && onModelChange(v)} disabled={disabled}>
        <SelectTrigger className="w-52">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {models.map((m) => (
            <SelectItem key={m} value={m}>
              {m}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
