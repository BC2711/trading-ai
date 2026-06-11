import { Plus } from "lucide-react";
import { useState } from "react";

import type { EconomicCalendarEventCreate, ImpactLevel } from "../../api/calendarApi";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Input } from "../ui/Input";
import { Select } from "../ui/Select";

type CalendarEventFormProps = {
  loading?: boolean;
  onSubmit: (event: EconomicCalendarEventCreate) => void;
};

const initialState = {
  event_name: "",
  country: "",
  impact_level: "medium" as ImpactLevel,
  event_datetime: "",
  affected_assets: "",
  previous_value: "",
  forecast_value: "",
  actual_value: ""
};

export function CalendarEventForm({ loading = false, onSubmit }: CalendarEventFormProps) {
  const [form, setForm] = useState(initialState);

  const submit = () => {
    if (!form.event_name.trim() || !form.country.trim() || !form.event_datetime) return;
    onSubmit({
      event_name: form.event_name.trim(),
      country: form.country.trim(),
      impact_level: form.impact_level,
      event_datetime: new Date(form.event_datetime).toISOString(),
      affected_assets: form.affected_assets.split(",").map((asset) => asset.trim().toUpperCase()).filter(Boolean),
      previous_value: form.previous_value.trim() || null,
      forecast_value: form.forecast_value.trim() || null,
      actual_value: form.actual_value.trim() || null
    });
    setForm(initialState);
  };

  return (
    <Card className="p-4 sm:p-5">
      <div className="mb-4">
        <h3 className="text-base font-black text-slate-950 dark:text-white">Add Event</h3>
        <p className="text-xs font-semibold text-slate-500 dark:text-white/45">Create a custom economic release or market blackout window.</p>
      </div>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Input label="Event Name" value={form.event_name} onChange={(event) => setForm({ ...form, event_name: event.target.value })} />
        <Input label="Country" value={form.country} onChange={(event) => setForm({ ...form, country: event.target.value })} />
        <Select
          label="Impact"
          value={form.impact_level}
          onChange={(event) => setForm({ ...form, impact_level: event.target.value as ImpactLevel })}
          options={[
            { label: "High", value: "high" },
            { label: "Medium", value: "medium" },
            { label: "Low", value: "low" }
          ]}
        />
        <Input label="Date/Time" type="datetime-local" value={form.event_datetime} onChange={(event) => setForm({ ...form, event_datetime: event.target.value })} />
        <Input label="Affected Assets" placeholder="USD, BTCUSDT" value={form.affected_assets} onChange={(event) => setForm({ ...form, affected_assets: event.target.value })} />
        <Input label="Previous" value={form.previous_value} onChange={(event) => setForm({ ...form, previous_value: event.target.value })} />
        <Input label="Forecast" value={form.forecast_value} onChange={(event) => setForm({ ...form, forecast_value: event.target.value })} />
        <Input label="Actual" value={form.actual_value} onChange={(event) => setForm({ ...form, actual_value: event.target.value })} />
      </div>
      <div className="mt-4 flex justify-end">
        <Button icon={Plus} loading={loading} onClick={submit} disabled={!form.event_name.trim() || !form.country.trim() || !form.event_datetime || loading}>
          Add event
        </Button>
      </div>
    </Card>
  );
}
