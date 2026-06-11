import { Bot, UserRound } from "lucide-react";

import type { CopilotMessage } from "../../api/copilotApi";
import { cn } from "../../utils/cn";
import { Card } from "../ui/Card";
import { Skeleton } from "../ui/LoadingSpinner";
import { CopilotCards } from "./CopilotCards";

type CopilotMessageListProps = {
  messages: CopilotMessage[];
  loading?: boolean;
};

export function CopilotMessageList({ messages, loading = false }: CopilotMessageListProps) {
  return (
    <Card className="min-h-[520px] p-4 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-black text-slate-950 dark:text-white">Message History</h2>
          <p className="text-xs font-semibold text-slate-500 dark:text-white/45">Grounded in portfolio, risk, scanner, strategy, and AI data</p>
        </div>
        <span className="rounded-[8px] border border-white/15 bg-white/10 px-3 py-1 text-xs font-bold text-slate-600 dark:text-white/60">
          {messages.length} messages
        </span>
      </div>

      <div className="grid max-h-[620px] gap-4 overflow-y-auto pr-1">
        {loading ? (
          <>
            <Skeleton className="h-20" />
            <Skeleton className="h-32" />
          </>
        ) : null}

        {!loading && messages.length === 0 ? (
          <div className="grid min-h-[340px] place-items-center rounded-[8px] border border-dashed border-white/20 bg-white/5 p-6 text-center">
            <div>
              <Bot className="mx-auto mb-3 text-cyan-600 dark:text-cyan-200" size={32} aria-hidden />
              <p className="text-sm font-black text-slate-950 dark:text-white">Ask the copilot about your trading workspace</p>
              <p className="mt-2 max-w-md text-sm font-medium leading-6 text-slate-500 dark:text-white/50">
                It can explain signals, rejected trades, portfolio risk, strategy performance, market outlook, and model decisions.
              </p>
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <article
            key={message.id}
            className={cn(
              "rounded-[8px] border p-4",
              message.role === "user"
                ? "ml-auto max-w-[760px] border-cyan-300/25 bg-cyan-400/10"
                : "mr-auto w-full border-white/15 bg-white/10 dark:bg-white/5"
            )}
          >
            <div className="flex items-start gap-3">
              <span
                className={cn(
                  "grid size-9 shrink-0 place-items-center rounded-[8px]",
                  message.role === "user"
                    ? "bg-cyan-400/15 text-cyan-700 dark:text-cyan-100"
                    : "bg-violet-400/15 text-violet-700 dark:text-violet-100"
                )}
              >
                {message.role === "user" ? <UserRound size={17} aria-hidden /> : <Bot size={17} aria-hidden />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-black capitalize text-slate-950 dark:text-white">{message.role}</p>
                  <time className="text-xs font-semibold text-slate-500 dark:text-white/40">{formatTime(message.created_at)}</time>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm font-medium leading-6 text-slate-700 dark:text-white/70">{message.content}</p>
                {message.role === "assistant" ? <CopilotCards cards={message.cards} /> : null}
              </div>
            </div>
          </article>
        ))}
      </div>
    </Card>
  );
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}
