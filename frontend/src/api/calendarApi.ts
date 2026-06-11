import { apiClient } from "../services/api";

export type ImpactLevel = "low" | "medium" | "high";

export type EconomicCalendarEvent = {
  id: number;
  event_name: string;
  country: string;
  impact_level: ImpactLevel;
  event_datetime: string;
  affected_assets: string[];
  previous_value: string | null;
  forecast_value: string | null;
  actual_value: string | null;
  trading_blackout_warning: string;
  high_impact: boolean;
  created_at: string;
};

export type EconomicCalendarEventCreate = {
  event_name: string;
  country: string;
  impact_level: ImpactLevel;
  event_datetime: string;
  affected_assets: string[];
  previous_value?: string | null;
  forecast_value?: string | null;
  actual_value?: string | null;
};

export type CalendarFilters = {
  country?: string;
  impact_level?: ImpactLevel | "";
  asset?: string;
  start?: string;
  end?: string;
};

export async function fetchCalendarEvents(filters: CalendarFilters = {}): Promise<EconomicCalendarEvent[]> {
  const response = await apiClient.get<EconomicCalendarEvent[]>("/api/calendar/events", {
    params: {
      country: filters.country || undefined,
      impact_level: filters.impact_level || undefined,
      asset: filters.asset || undefined,
      start: filters.start || undefined,
      end: filters.end || undefined
    }
  });
  return response.data;
}

export async function fetchHighImpactEvents(): Promise<EconomicCalendarEvent[]> {
  const response = await apiClient.get<EconomicCalendarEvent[]>("/api/calendar/high-impact");
  return response.data;
}

export async function createCalendarEvent(payload: EconomicCalendarEventCreate): Promise<EconomicCalendarEvent> {
  const response = await apiClient.post<EconomicCalendarEvent>("/api/calendar/events", payload);
  return response.data;
}
