import { Bell, ChevronDown, Gauge, Menu, Moon, Plus, Sun } from "lucide-react";
import { useState } from "react";

import { Badge } from "../ui/Badge";
import { Button, IconButton } from "../ui/Button";
import { Dropdown } from "../ui/Dropdown";
import { SearchInput } from "../ui/SearchInput";

type NavbarProps = {
  isDark: boolean;
  onThemeToggle: () => void;
  onMobileMenu: () => void;
};

export function Navbar({ isDark, onThemeToggle, onMobileMenu }: NavbarProps) {
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

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
          <Button variant="primary" icon={Plus} className="hidden sm:inline-flex">
            New strategy
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
                  MC
                </span>
                <span className="hidden sm:inline">Maya</span>
                <ChevronDown size={14} aria-hidden />
              </button>
            }
          >
            <UserProfileMenu />
          </Dropdown>
        </div>

        <SearchInput wrapperClassName="flex w-full md:hidden" placeholder="Search symbols, orders, alerts" aria-label="Global search" />
      </div>
    </header>
  );
}

function NotificationPanel() {
  const items = [
    { title: "BTC confidence crossed 80%", tone: "info" as const, time: "2m" },
    { title: "Risk cap protected on EURUSD", tone: "success" as const, time: "14m" },
    { title: "Volatility elevated on NQ", tone: "warning" as const, time: "31m" }
  ];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between px-2 py-1">
        <strong className="text-sm text-slate-900 dark:text-white">Notifications</strong>
        <Badge tone="info">3 new</Badge>
      </div>
      {items.map((item) => (
        <button
          key={item.title}
          type="button"
          className="flex w-full items-start gap-3 rounded-[8px] border border-white/10 bg-white/10 p-3 text-left transition hover:bg-white/20 dark:bg-white/5"
        >
          <span
            className={
              item.tone === "success"
                ? "mt-1 size-2 rounded-full bg-emerald-400"
                : item.tone === "warning"
                  ? "mt-1 size-2 rounded-full bg-amber-400"
                  : "mt-1 size-2 rounded-full bg-cyan-400"
            }
          />
          <span className="grid flex-1 gap-1">
            <span className="text-sm font-semibold text-slate-800 dark:text-white/90">{item.title}</span>
            <span className="text-xs text-slate-500 dark:text-white/50">{item.time} ago</span>
          </span>
        </button>
      ))}
    </div>
  );
}

function UserProfileMenu() {
  return (
    <div className="space-y-2">
      <div className="rounded-[8px] border border-white/10 bg-white/10 p-3 dark:bg-white/5">
        <p className="text-sm font-bold text-slate-900 dark:text-white">Maya Chen</p>
        <p className="text-xs text-slate-500 dark:text-white/50">Portfolio Operations</p>
      </div>
      {["Profile", "Billing", "Security", "Sign out"].map((item) => (
        <button
          key={item}
          type="button"
          className="w-full rounded-[8px] px-3 py-2 text-left text-sm font-semibold text-slate-700 transition hover:bg-white/20 dark:text-white/75 dark:hover:bg-white/10"
        >
          {item}
        </button>
      ))}
    </div>
  );
}
