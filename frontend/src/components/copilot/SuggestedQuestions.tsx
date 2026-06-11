import { Lightbulb } from "lucide-react";

import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

type SuggestedQuestionsProps = {
  questions: string[];
  onSelect: (question: string) => void;
};

export function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="mb-3 flex items-center gap-2">
        <Lightbulb size={16} className="text-amber-600 dark:text-amber-200" aria-hidden />
        <h2 className="text-sm font-black text-slate-950 dark:text-white">Suggested Questions</h2>
      </div>
      <div className="flex flex-wrap gap-2">
        {questions.map((question) => (
          <Button key={question} variant="outline" onClick={() => onSelect(question)} className="min-h-9 px-3 text-xs">
            {question}
          </Button>
        ))}
      </div>
    </Card>
  );
}
