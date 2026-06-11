import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";

import type { CopilotMessage } from "../api/copilotApi";
import { fetchCopilotHistory, sendCopilotMessage } from "../api/copilotApi";
import { CopilotComposer } from "../components/copilot/CopilotComposer";
import { CopilotMessageList } from "../components/copilot/CopilotMessageList";
import { SuggestedQuestions } from "../components/copilot/SuggestedQuestions";
import { Alert } from "../components/ui/Alert";
import { Card } from "../components/ui/Card";

const fallbackQuestions = [
  "Why was the latest signal generated?",
  "Why was my latest trade rejected?",
  "What is my current portfolio risk?",
  "Which strategy is performing best?",
  "What is the current market outlook?",
  "Explain the latest AI model decision."
];

export function CopilotPage() {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const historyQuery = useQuery({ queryKey: ["copilot", "history"], queryFn: fetchCopilotHistory });
  const chatMutation = useMutation({
    mutationFn: sendCopilotMessage,
    onSuccess: (response) => {
      queryClient.setQueryData<CopilotMessage[]>(["copilot", "history"], (current = []) => [
        ...current,
        response.user_message,
        response.assistant_message
      ]);
      setDraft("");
    }
  });

  const messages = historyQuery.data ?? [];
  const suggestedQuestions = useMemo(() => {
    const latestAssistant = [...messages].reverse().find((message) => message.role === "assistant");
    return latestAssistant?.suggested_questions.length ? latestAssistant.suggested_questions : fallbackQuestions;
  }, [messages]);

  const submit = () => {
    const message = draft.trim();
    if (!message || chatMutation.isPending) return;
    chatMutation.mutate(message);
  };

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Bot size={14} aria-hidden />
              AI Trading Copilot
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">AI Copilot</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Ask for explanations across signals, rejected trades, portfolio risk, strategy performance, market outlook, and model decisions.
            </p>
          </div>
          <div className="grid min-w-[220px] gap-1 rounded-[8px] border border-white/10 bg-white/10 p-3 text-right backdrop-blur-md dark:bg-white/5">
            <span className="inline-flex items-center justify-end gap-2 text-xs font-bold uppercase text-slate-500 dark:text-white/40">
              <Sparkles size={13} aria-hidden />
              Context sources
            </span>
            <span className="text-sm font-black text-slate-950 dark:text-white">Portfolio, Risk, AI, Scanner</span>
          </div>
        </div>
      </Card>

      {historyQuery.isError ? <Alert tone="error">Unable to load copilot history.</Alert> : null}
      {chatMutation.isError ? <Alert tone="error">The copilot could not answer that question.</Alert> : null}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px] xl:gap-6">
        <CopilotMessageList messages={messages} loading={historyQuery.isLoading} />
        <div className="grid content-start gap-4">
          <SuggestedQuestions
            questions={suggestedQuestions}
            onSelect={(question) => {
              setDraft(question);
            }}
          />
          <CopilotComposer value={draft} loading={chatMutation.isPending} onChange={setDraft} onSubmit={submit} />
        </div>
      </section>
    </div>
  );
}
