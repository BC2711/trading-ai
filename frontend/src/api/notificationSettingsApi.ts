import { apiClient } from "../services/api";
import type { NotificationResource } from "../services/api";

export type NotificationChannel = {
  key: "in_app" | "email" | "telegram" | "whatsapp" | "discord";
  label: string;
  enabled: boolean;
  configured: boolean;
  placeholder: boolean;
};

export type NotificationEventCategory = "trade" | "risk" | "ai" | "system";

export type NotificationEvent = {
  key: string;
  label: string;
  category: NotificationEventCategory;
  enabled: boolean;
};

export type NotificationSettings = {
  in_app_enabled: boolean;
  email_enabled: boolean;
  telegram_enabled: boolean;
  whatsapp_enabled: boolean;
  discord_enabled: boolean;
  trade_alerts: boolean;
  risk_alerts: boolean;
  ai_alerts: boolean;
  system_alerts: boolean;
  channels: NotificationChannel[];
  events: NotificationEvent[];
  updated_at: string;
};

export type NotificationSettingsUpdate = Partial<
  Pick<
    NotificationSettings,
    | "in_app_enabled"
    | "email_enabled"
    | "telegram_enabled"
    | "whatsapp_enabled"
    | "discord_enabled"
    | "trade_alerts"
    | "risk_alerts"
    | "ai_alerts"
    | "system_alerts"
  >
>;

export type NotificationMarkReadRequest = {
  notification_ids?: number[];
  all?: boolean;
};

export type NotificationMarkReadResponse = {
  updated_count: number;
  notifications: NotificationResource[];
};

export async function fetchNotificationSettings(): Promise<NotificationSettings> {
  const response = await apiClient.get<NotificationSettings>("/api/notifications/settings");
  return response.data;
}

export async function updateNotificationSettings(
  payload: NotificationSettingsUpdate
): Promise<NotificationSettings> {
  const response = await apiClient.put<NotificationSettings>("/api/notifications/settings", payload);
  return response.data;
}

export async function markNotificationsRead(
  payload: NotificationMarkReadRequest
): Promise<NotificationMarkReadResponse> {
  const response = await apiClient.post<NotificationMarkReadResponse>("/api/notifications/mark-read", payload);
  return response.data;
}
