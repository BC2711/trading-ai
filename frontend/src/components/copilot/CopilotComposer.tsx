import { SendHorizontal } from "lucide-react";
import { FormEvent, KeyboardEvent } from "react";

import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Textarea } from "../ui/Textarea";

type CopilotComposerProps = {
  value: string;
  loading?: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function CopilotComposer({ value, loading = false, onChange, onSubmit }: CopilotComposerProps) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  };

  return (
    <Card className="p-4 sm:p-5">
      <form onSubmit={submit} className="grid gap-3">
        <Textarea
          label="Ask the AI Trading Copilot"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Why was the latest signal generated?"
          className="min-h-28"
        />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs font-semibold text-slate-500 dark:text-white/45">Enter sends, Shift+Enter adds a new line.</p>
          <Button icon={SendHorizontal} loading={loading} disabled={!value.trim() || loading} type="submit">
            Send
          </Button>
        </div>
      </form>
    </Card>
  );
}
