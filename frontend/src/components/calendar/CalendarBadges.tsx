import { AlertTriangle, Info, ShieldAlert } from "lucide-react";

import type { ImpactLevel } from "../../api/calendarApi";
import { Badge } from "../ui/Badge";

export function ImpactBadge({ impact }: { impact: ImpactLevel }) {
  const Icon = impact === "high" ? ShieldAlert : impact === "medium" ? AlertTriangle : Info;
  return (
    <Badge tone={impact === "high" ? "error" : impact === "medium" ? "warning" : "neutral"} className="capitalize">
      <Icon size={13} aria-hidden />
      {impact}
    </Badge>
  );
}
