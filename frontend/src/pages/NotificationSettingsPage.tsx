import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Save } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { NotificationSettingsUpdate } from "../api/notificationSettingsApi";
import { fetchNotificationSettings, updateNotificationSettings } from "../api/notificationSettingsApi";
import { NotificationSettingsPanel } from "../components/notifications";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { Skeleton } from "../components/ui/LoadingSpinner";

const defaultSettings: NotificationSettingsUpdate = {
  in_app_enabled: true,
  email_enabled: false,
  telegram_enabled: false,
  whatsapp_enabled: false,
  discord_enabled: false,
  trade_alerts: true,
  risk_alerts: true,
  ai_alerts: true,
  system_alerts: true
};

export function NotificationSettingsPage() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ["notifications", "settings"],
    queryFn: fetchNotificationSettings
  });
  const [form, setForm] = useState<NotificationSettingsUpdate>(defaultSettings);

  useEffect(() => {
    if (settingsQuery.data) {
      setForm({
        in_app_enabled: settingsQuery.data.in_app_enabled,
        email_enabled: settingsQuery.data.email_enabled,
        telegram_enabled: settingsQuery.data.telegram_enabled,
        whatsapp_enabled: settingsQuery.data.whatsapp_enabled,
        discord_enabled: settingsQuery.data.discord_enabled,
        trade_alerts: settingsQuery.data.trade_alerts,
        risk_alerts: settingsQuery.data.risk_alerts,
        ai_alerts: settingsQuery.data.ai_alerts,
        system_alerts: settingsQuery.data.system_alerts
      });
    }
  }, [settingsQuery.data]);

  const updateMutation = useMutation({
    mutationFn: updateNotificationSettings,
    onSuccess: (settings) => {
      queryClient.setQueryData(["notifications", "settings"], settings);
      queryClient.invalidateQueries({ queryKey: ["navigation"] });
    }
  });

  const enabledChannels = useMemo(
    () => settingsQuery.data?.channels.filter((channel) => channel.enabled).length ?? 0,
    [settingsQuery.data]
  );
  const enabledEvents = useMemo(
    () => settingsQuery.data?.events.filter((event) => event.enabled).length ?? 0,
    [settingsQuery.data]
  );

  return (
    <div className="grid gap-4 xl:gap-6">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-bold text-cyan-700 backdrop-blur-md dark:text-cyan-100">
              <Bell size={14} aria-hidden />
              Notification controls
            </div>
            <h1 className="text-3xl font-black text-slate-950 dark:text-white">Notification Settings</h1>
            <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-600 dark:text-white/55">
              Configure delivery channels and alert groups for trade, risk, AI, and system events.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row lg:items-center">
            <div className="grid min-w-[168px] gap-1 rounded-[8px] border border-white/10 bg-white/10 p-3 text-right backdrop-blur-md dark:bg-white/5">
              <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">Enabled channels</span>
              <span className="text-2xl font-black text-slate-950 dark:text-white">{enabledChannels}</span>
            </div>
            <div className="grid min-w-[168px] gap-1 rounded-[8px] border border-white/10 bg-white/10 p-3 text-right backdrop-blur-md dark:bg-white/5">
              <span className="text-xs font-bold uppercase text-slate-500 dark:text-white/40">Active events</span>
              <span className="text-2xl font-black text-slate-950 dark:text-white">{enabledEvents}</span>
            </div>
            <Button icon={Save} loading={updateMutation.isPending} onClick={() => updateMutation.mutate(form)}>
              Save settings
            </Button>
          </div>
        </div>
      </Card>

      {settingsQuery.isError ? <Alert tone="error">Unable to load notification settings.</Alert> : null}
      {updateMutation.isError ? <Alert tone="error">Unable to update notification settings.</Alert> : null}
      {updateMutation.isSuccess ? <Alert tone="success">Notification settings updated.</Alert> : null}

      {settingsQuery.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-32" />
          ))}
        </div>
      ) : (
        <NotificationSettingsPanel value={form} settings={settingsQuery.data} onChange={setForm} />
      )}
    </div>
  );
}
