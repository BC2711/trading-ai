import { Bell, Bot, Mail, MessageCircle, Radio, Send, ShieldAlert, Smartphone, TrendingUp, Zap } from "lucide-react";

import type { NotificationSettings, NotificationSettingsUpdate } from "../../api/notificationSettingsApi";
import { Card } from "../ui/Card";
import { NotificationToggle } from "./NotificationToggle";

type NotificationSettingsPanelProps = {
  value: NotificationSettingsUpdate;
  settings?: NotificationSettings;
  onChange: (value: NotificationSettingsUpdate) => void;
};

const channelControls = [
  { key: "in_app_enabled", channelKey: "in_app", label: "In-app", detail: "Workspace alerts and live notification stream.", icon: Bell, placeholder: false },
  { key: "email_enabled", channelKey: "email", label: "Email", detail: "SMTP email delivery.", icon: Mail, placeholder: false },
  { key: "telegram_enabled", channelKey: "telegram", label: "Telegram", detail: "Telegram bot delivery.", icon: Send, placeholder: false },
  { key: "whatsapp_enabled", channelKey: "whatsapp", label: "WhatsApp", detail: "WhatsApp Cloud API delivery.", icon: Smartphone, placeholder: false },
  { key: "discord_enabled", channelKey: "discord", label: "Discord", detail: "Discord webhook delivery.", icon: MessageCircle, placeholder: false }
] as const;

const alertControls = [
  { key: "trade_alerts", label: "Trade alerts", detail: "Executions, rejections, stop loss, and take profit events.", icon: TrendingUp },
  { key: "risk_alerts", label: "Risk alerts", detail: "Daily loss limit and drawdown warnings.", icon: ShieldAlert },
  { key: "ai_alerts", label: "AI alerts", detail: "AI signals and model training completion.", icon: Bot },
  { key: "system_alerts", label: "System alerts", detail: "Backtest completion and broker disconnect notices.", icon: Zap }
] as const;

export function NotificationSettingsPanel({ value, settings, onChange }: NotificationSettingsPanelProps) {
  const setField = (key: keyof NotificationSettingsUpdate, checked: boolean) => onChange({ ...value, [key]: checked });

  return (
    <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-[8px] bg-cyan-400/15 text-cyan-700 dark:text-cyan-100">
            <Radio size={18} aria-hidden />
          </span>
          <div>
            <h2 className="text-lg font-black text-slate-950 dark:text-white">Channels</h2>
            <p className="text-xs font-semibold text-slate-500 dark:text-white/45">Delivery routes</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          {channelControls.map((control) => {
            const channel = settings?.channels.find((item) => item.key === control.channelKey);
            return (
              <NotificationToggle
                key={control.key}
                label={control.label}
                detail={control.detail}
                icon={control.icon}
                placeholder={control.placeholder}
                configured={channel?.configured ?? true}
                checked={Boolean(value[control.key])}
                onChange={(checked) => setField(control.key, checked)}
              />
            );
          })}
        </div>
      </Card>

      <Card className="p-4 sm:p-5">
        <div className="mb-4 flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-[8px] bg-emerald-400/15 text-emerald-700 dark:text-emerald-100">
            <Bell size={18} aria-hidden />
          </span>
          <div>
            <h2 className="text-lg font-black text-slate-950 dark:text-white">Alert Groups</h2>
            <p className="text-xs font-semibold text-slate-500 dark:text-white/45">Event categories</p>
          </div>
        </div>
        <div className="grid gap-3">
          {alertControls.map((control) => (
            <NotificationToggle
              key={control.key}
              label={control.label}
              detail={control.detail}
              icon={control.icon}
              checked={Boolean(value[control.key])}
              onChange={(checked) => setField(control.key, checked)}
            />
          ))}
        </div>
      </Card>

      <Card className="p-0 xl:col-span-2">
        <div className="border-b border-white/10 p-4 sm:p-5">
          <h2 className="text-lg font-black text-slate-950 dark:text-white">Notification Events</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-white/10 text-sm">
            <thead className="bg-white/5 text-xs uppercase text-slate-500 dark:text-white/45">
              <tr>
                <th className="px-4 py-3 text-left font-black">Event</th>
                <th className="px-4 py-3 text-left font-black">Group</th>
                <th className="px-4 py-3 text-left font-black">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {(settings?.events ?? []).map((event) => (
                <tr key={event.key}>
                  <td className="px-4 py-3 font-bold text-slate-800 dark:text-white/85">{event.label}</td>
                  <td className="px-4 py-3 font-semibold capitalize text-slate-500 dark:text-white/50">{event.category}</td>
                  <td className="px-4 py-3">
                    <span className={event.enabled ? "text-emerald-700 dark:text-emerald-100" : "text-slate-500 dark:text-white/45"}>
                      {event.enabled ? "Enabled" : "Muted"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
