import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

import type { ImpactLevel, SentimentStatus } from "../../api/sentimentApi";
import { Badge } from "../ui/Badge";

export function SentimentBadge({ status }: { status: SentimentStatus }) {
  const Icon = status === "bullish" ? ArrowUpRight : status === "bearish" ? ArrowDownRight : ArrowRight;
  return (
    <Badge tone={status === "bullish" ? "success" : status === "bearish" ? "error" : "warning"} className="capitalize">
      <Icon size={13} aria-hidden />
      {status}
    </Badge>
  );
}

export function ImpactBadge({ impact }: { impact: ImpactLevel }) {
  return (
    <Badge tone={impact === "high" ? "error" : impact === "medium" ? "warning" : "neutral"} className="capitalize">
      {impact}
    </Badge>
  );
}
