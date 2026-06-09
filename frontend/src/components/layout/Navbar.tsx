import { Bell, ChevronDown, Gauge, Menu, Moon, Plus, Sun } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Badge } from "../ui/Badge";
import { Button, IconButton } from "../ui/Button";
import { Dropdown } from "../ui/Dropdown";
import { SearchInput } from "../ui/SearchInput";
import { fetchAuditEvents, fetchCurrentUser, logout } from "../../services/api";

type NavbarProps = {
  isDark: boolean;
  onThemeToggle: () => void;
  onMobileMenu: () => void;
};

export function Navbar({ isDark, onThemeToggle, onMobileMenu }: NavbarProps) {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const currentUserQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: fetchCurrentUser,
    staleTime: 1000 * 60 * 5
  });
  const currentUser = currentUserQuery.data;
  const initials = currentUser?.name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "TO";

  return (
    <header className="sticky top-3 z-40 rounded-[8px] border border-white/20 bg-white/10 p-3 shadow-2xl shadow-slate-950/10 backdrop-blur-xl dark:border-white/10 dark:bg-white/5 dark:shadow-black/25 xl:top-6">
      <div className="flex flex-wrap items-center gap-3 lg:flex-nowrap">
        <IconButton label="Open navigation" icon={Menu} onClick={onMobileMenu} className="lg:hidden" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-500 dark:text-white/45">
            <Gauge size={14} aria-hidden />
            <span>Workspace</span>
            <span>/</span>
            <span className="text-slate-800 dark:text-white/80">AI Signals</span>
          </div>
          <SearchInput wrapperClassName="mt-2 hidden max-w-2xl md:flex" placeholder="Search symbols, orders, alerts" aria-label="Global search" />
        </div>

        <div className="flex items-center gap-2">
          <Button variant="primary" icon={Plus} className="hidden sm:inline-flex" onClick={() => { window.location.hash = "#/overview/settings"; }}>
            Strategy controls
          </Button>
          <IconButton label={isDark ? "Switch to light mode" : "Switch to dark mode"} icon={isDark ? Sun : Moon} onClick={onThemeToggle} />
          <Dropdown
            open={notificationsOpen}
            onOpenChange={setNotificationsOpen}
            trigger={<IconButton label="Notifications" icon={Bell} active={notificationsOpen} />}
          >
            <NotificationPanel />
          </Dropdown>
          <Dropdown
            open={profileOpen}
            onOpenChange={setProfileOpen}
            trigger={
              <button
                type="button"
                className="flex min-h-10 items-center gap-2 rounded-[8px] border border-white/20 bg-white/10 px-2 pr-3 text-sm font-bold text-slate-800 shadow-lg shadow-slate-950/5 backdrop-blur-lg transition hover:bg-white/20 dark:text-white dark:shadow-black/20"
                aria-label="Open user profile menu"
              >
                <span className="grid size-8 place-items-center rounded-[8px] bg-gradient-to-br from-emerald-300 to-cyan-500 text-xs text-white">
                  {initials}
                </span>
                <span className="hidden sm:inline">{currentUser?.name ?? "Operator"}</span>
                <ChevronDown size={14} aria-hidden />
              </button>
            }
          >
            <UserProfileMenu name={currentUser?.name ?? "Trading Operator"} role={currentUser?.role ?? "operator"} />
          </Dropdown>
        </div>

        <SearchInput wrapperClassName="flex w-full md:hidden" placeholder="Search symbols, orders, alerts" aria-label="Global search" />
      </div>
    </header>
  );
}

function NotificationPanel() {
  const eventsQuery = useQuery({
    queryKey: ["audit-events", "notifications"],
    queryFn: () => fetchAuditEvents({ limit: 3 })
  });
  const items = eventsQuery.data ?? [];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-2 py-1">
        <strong className="text-sm text-slate-900 dark:text-white">Notifications</strong>
        <Badge tone="info">{items.length} recent</Badge>
      </div>
      {eventsQuery.isLoading ? (
        <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 text-sm font-semibold text-slate-500 dark:bg-white/5 dark:text-white/50">
          Loading recent events
        </div>
      ) : null}
      {!eventsQuery.isLoading && items.length === 0 ? (
        <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 text-sm font-semibold text-slate-500 dark:bg-white/5 dark:text-white/50">
          No audit events yet
        </div>
      ) : null}
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className="flex w-full items-start gap-3 rounded-[8px] border border-white/10 bg-white/10 p-3 text-left transition hover:bg-white/20 dark:bg-white/5"
          onClick={() => { window.location.hash = "#/activity"; }}
        >
          <span
            className={
              item.severity === "warning"
                  ? "mt-1 size-2 rounded-full bg-amber-400"
                  : item.severity === "error"
                    ? "mt-1 size-2 rounded-full bg-rose-400"
                    : "mt-1 size-2 rounded-full bg-cyan-400"
            }
          />
          <span className="grid flex-1 gap-1">
            <span className="text-sm font-semibold text-slate-800 dark:text-white/90">{item.message}</span>
            <span className="text-xs text-slate-500 dark:text-white/50">{formatRelativeTime(item.created_at)}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

function UserProfileMenu({ name, role }: { name: string; role: string }) {
  return (
    <div className="space-y-2">
      <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
        <p className="text-sm font-bold text-slate-900 dark:text-white">{name}</p>
        <p className="text-xs capitalize text-slate-500 dark:text-white/50">{role}</p>
      </div>
      {[
        ["Dashboard", "#/overview"],
        ["Trading", "#/trading"],
        ["Audit Log", "#/activity/audit"],
        ["Sign out", "logout"]
      ].map(([item, href]) => (
        <button
          key={item}
          type="button"
          className="w-full rounded-[8px] px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-white/20 dark:text-white/75 dark:hover:bg-white/10"
          onClick={() => {
            if (href === "logout") {
              logout();
              window.location.reload();
              return;
            }
            window.location.hash = href;
          }}
        >
          {item}
        </button>
      ))}
    </div>
  );
}

function formatRelativeTime(value: string) {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "Just now";
  }

  const minutes = Math.floor(Math.max(0, Date.now() - timestamp) / 60000);
  if (minutes < 1) {
    return "Just now";
  }
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}
