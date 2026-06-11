import { AnimatePresence, motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Bell,
  BrainCircuit,
  CalendarDays,
  ChevronDown,
  Clock3,
  KeyRound,
  LayoutDashboard,
  Menu,
  MessageCircle,
  Newspaper,
  ScanSearch,
  Settings,
  Sparkles,
  SlidersHorizontal,
  ShieldCheck,
  TrendingUp,
  Users,
  Wallet,
  X,
  Zap
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState, useCallback, useRef } from "react";
import { createPortal } from "react-dom";

import { fetchCurrentUser, fetchNavigation } from "../../services/api";
import type { NavigationItem } from "../../services/api";
import { cn } from "../../utils/cn";
import { IconButton } from "../ui/Button";

type ChildNavItem = {
  label: string;
  icon: LucideIcon;
  href: string;
  permission: string;
  active?: boolean;
  badge?: string;
  badgeColor?: string;
};

type NavItem = {
  label: string;
  icon: LucideIcon;
  href: string;
  permission: string;
  active?: boolean;
  children: ChildNavItem[];
};

const iconMap: Record<string, LucideIcon> = {
  activity: Activity,
  bell: Bell,
  brain: BrainCircuit,
  "calendar-days": CalendarDays,
  clock: Clock3,
  key: KeyRound,
  "layout-dashboard": LayoutDashboard,
  "message-circle": MessageCircle,
  newspaper: Newspaper,
  "scan-search": ScanSearch,
  "shield-check": ShieldCheck,
  "sliders-horizontal": SlidersHorizontal,
  sparkles: Sparkles,
  "trending-up": TrendingUp,
  users: Users,
  wallet: Wallet
};

const fallbackNavItems: NavItem[] = [
  {
    label: "Overview",
    icon: LayoutDashboard,
    href: "#/overview",
    permission: "dashboard:view",
    children: [
      { label: "Portfolio", icon: Wallet, href: "#/overview/portfolio", permission: "portfolio:view" },
      { label: "Signals", icon: Sparkles, href: "#/overview/signals", permission: "signals:view" },
      { label: "Strategy Controls", icon: SlidersHorizontal, href: "#/overview/settings", permission: "strategies:update" }
    ]
  },
  {
    label: "Administration",
    icon: Users,
    href: "#/users",
    permission: "users:manage",
    children: [
      { label: "Users", icon: Users, href: "#/users", permission: "users:manage" },
      { label: "API Keys", icon: KeyRound, href: "#/api-keys", permission: "api-credentials:manage" },
      { label: "Notification Settings", icon: Bell, href: "#/administration/notification-settings", permission: "notifications:manage" }
    ]
  },
  {
    label: "Research",
    icon: Sparkles,
    href: "#/strategies",
    permission: "strategies:view",
    children: [
      { label: "Strategies", icon: SlidersHorizontal, href: "#/strategies", permission: "strategies:view" },
      { label: "Strategy Builder", icon: Activity, href: "#/strategies/builder", permission: "strategies:update" },
      { label: "Backtests", icon: Activity, href: "#/backtests", permission: "backtests:view" },
      { label: "Walk-Forward Testing", icon: Activity, href: "#/backtests/walk-forward", permission: "backtests:run" },
      { label: "AI Models", icon: BrainCircuit, href: "#/ai-models", permission: "ai-models:view" }
    ]
  },
  {
    label: "Market",
    icon: ScanSearch,
    href: "#/market/scanner",
    permission: "signals:view",
    children: [
      { label: "Market Scanner", icon: ScanSearch, href: "#/market/scanner", permission: "signals:view" },
      { label: "News Sentiment", icon: Newspaper, href: "#/market/sentiment", permission: "signals:view" },
      { label: "Economic Calendar", icon: CalendarDays, href: "#/market/calendar", permission: "signals:view" }
    ]
  },
  {
    label: "AI",
    icon: BrainCircuit,
    href: "#/ai/copilot",
    permission: "ai-models:view",
    children: [
      { label: "AI Copilot", icon: MessageCircle, href: "#/ai/copilot", permission: "ai-analyses:view" },
      { label: "Model Training", icon: Activity, href: "#/ai/model-training", permission: "ai-models:manage" },
      { label: "Model Registry", icon: BrainCircuit, href: "#/ai/model-registry", permission: "ai-models:view" }
    ]
  },
  {
    label: "Trading",
    icon: TrendingUp,
    href: "#/trading",
    permission: "orders:view",
    children: [
      { label: "Portfolio", icon: Wallet, href: "#/trading/portfolio", permission: "portfolio:view" },
      { label: "Paper Trading", icon: Activity, href: "#/trading/paper", permission: "orders:create" },
      { label: "Broker Connections", icon: KeyRound, href: "#/trading/brokers", permission: "api-credentials:manage" },
      { label: "Orders", icon: Activity, href: "#/trading/orders", permission: "orders:view" },
      { label: "Positions", icon: Wallet, href: "#/trading/positions", permission: "positions:view" },
      { label: "Trade History", icon: Clock3, href: "#/trade-history", permission: "orders:view" }
    ]
  },
  {
    label: "Risk",
    icon: ShieldCheck,
    href: "#/risk-analytics",
    permission: "risk-settings:view",
    children: [
      { label: "Risk Settings", icon: SlidersHorizontal, href: "#/risk-settings", permission: "risk-settings:view" },
      { label: "Risk Analytics", icon: Activity, href: "#/risk-analytics", permission: "risk-settings:view" },
      { label: "Monte Carlo", icon: Activity, href: "#/risk/monte-carlo", permission: "risk-settings:view" }
    ]
  },
  {
    label: "Activity",
    icon: Activity,
    href: "#/activity",
    permission: "audit:view",
    children: [
      { label: "Timeline", icon: Clock3, href: "#/activity", permission: "audit:view" },
      { label: "Audit Log", icon: Users, href: "#/activity/audit", permission: "audit:view" },
      { label: "Logs", icon: Activity, href: "#/logs", permission: "logs:view" },
      { label: "Notifications", icon: Bell, href: "#/notifications", permission: "notifications:view" }
    ]
  }
];

const fallbackPermissions = fallbackNavItems.flatMap((item) => [
  item.permission,
  ...item.children.map((child) => child.permission)
]);

type SidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
  mobile?: boolean;
};

export function Sidebar({ collapsed, onToggle, mobile = false }: SidebarProps) {
  const currentUserQuery = useQuery({
    queryKey: ["current-user"],
    queryFn: fetchCurrentUser,
    staleTime: 1000 * 60 * 5
  });
  const navigationQuery = useQuery({
    queryKey: ["navigation"],
    queryFn: fetchNavigation,
    staleTime: 1000 * 60 * 5
  });
  const [expandedItem, setExpandedItem] = useState<string | null>("Overview");
  const [openTooltip, setOpenTooltip] = useState<string | null>(null);
  const [activeChildHref, setActiveChildHref] = useState<string | null>(null);
  const [currentHash, setCurrentHash] = useState(() => window.location.hash || "#/overview");
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const sidebarRef = useRef<HTMLElement>(null);
  const tooltipTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const permissions = new Set(currentUserQuery.data?.permissions ?? fallbackPermissions);
  const navItems = (navigationQuery.data?.length ? navigationQuery.data.map(mapNavigationItem) : fallbackNavItems)
    .filter((item) => permissions.has(item.permission))
    .map((item) => ({ ...item, children: item.children.filter((child) => permissions.has(child.permission)) }));

  const handleChildClick = useCallback((href: string) => {
    setActiveChildHref(href);
  }, []);

  useEffect(() => {
    const handleHashChange = () => setCurrentHash(window.location.hash || "#/overview");
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    if (collapsed) {
      setExpandedItem(null);
    } else {
      setExpandedItem((current) => current ?? "Overview");
      setOpenTooltip(null);
    }
  }, [collapsed]);

  const toggleExpand = (label: string, href: string) => {
    window.location.hash = href;
    if (!collapsed) {
      setExpandedItem((current) => (current === label ? null : label));
    }
  };

  const handleTooltipShow = (label: string, event: React.MouseEvent | React.FocusEvent) => {
    if (!collapsed) return;

    const target = event.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();

    setTooltipPosition({
      top: rect.top,
      left: rect.right + 14,
    });

    // Clear any pending hide timeout
    if (tooltipTimeoutRef.current) {
      clearTimeout(tooltipTimeoutRef.current);
    }

    setOpenTooltip(label);
  };

  const handleTooltipHide = () => {
    // Add slight delay to allow moving to tooltip
    tooltipTimeoutRef.current = setTimeout(() => {
      setOpenTooltip(null);
    }, 150);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (tooltipTimeoutRef.current) {
        clearTimeout(tooltipTimeoutRef.current);
      }
    };
  }, []);

  return (
    <>
      <motion.aside
        ref={sidebarRef}
        className={cn(
          "relative z-30 flex h-full min-h-[calc(100vh-1.5rem)] flex-col overflow-hidden",
          "rounded-2xl border border-white/20",
          "bg-gradient-to-b from-white/15 via-white/10 to-white/[0.07]",
          "dark:from-white/[0.08] dark:via-white/[0.04] dark:to-white/[0.01]",
          "p-3 shadow-2xl shadow-slate-950/15 backdrop-blur-2xl",
          "dark:border-white/[0.08] dark:shadow-black/40",
          "transition-[width] duration-500 ease-out",
          collapsed ? "w-20" : "w-[260px]",
          mobile && "w-[min(320px,calc(100vw-1.5rem))]",
          // Glass highlight overlay
          "before:pointer-events-none before:absolute before:inset-0 before:rounded-2xl",
          "before:bg-gradient-to-br before:from-white/20 before:via-white/5 before:to-transparent",
          "dark:before:from-white/[0.08] dark:before:via-transparent",
          // Inner glow ring
          "after:pointer-events-none after:absolute after:inset-0 after:rounded-2xl",
          "after:ring-1 after:ring-inset after:ring-white/10 dark:after:ring-white/[0.06]"
        )}
        initial={{ x: mobile ? -320 : 0, opacity: mobile ? 0 : 1 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: -320, opacity: 0 }}
        transition={{ type: "spring", damping: 25, stiffness: 300 }}
        aria-label="Primary navigation"
      >
        {/* Ambient background particles */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl">
          <motion.div
            className="absolute -right-20 -top-20 size-48 rounded-full bg-gradient-to-br from-cyan-400/15 to-violet-400/10 blur-3xl"
            animate={{
              scale: [1, 1.15, 1],
              opacity: [0.25, 0.4, 0.25],
              rotate: [0, 90, 0]
            }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute -bottom-20 -left-20 size-48 rounded-full bg-gradient-to-br from-blue-400/10 to-purple-400/15 blur-3xl"
            animate={{
              scale: [1.15, 1, 1.15],
              opacity: [0.4, 0.25, 0.4],
              rotate: [90, 0, 90]
            }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute left-1/2 top-1/2 size-32 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-br from-cyan-300/5 to-blue-400/5 blur-2xl"
            animate={{
              scale: [0.8, 1.2, 0.8],
              opacity: [0.1, 0.3, 0.1]
            }}
            transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>

        <SidebarHeader collapsed={collapsed} mobile={mobile} onToggle={onToggle} />

        <nav className="relative z-10 mt-6 grid gap-1.5" aria-label="Main navigation">
          <AnimatePresence mode="popLayout">
            {navItems.map((item, index) => {
              const isExpanded = !collapsed && expandedItem === item.label;
              const active = isNavItemActive(item, currentHash);

              return (
                <motion.div
                  key={item.label}
                  className="relative"
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  transition={{
                    delay: index * 0.05,
                    duration: 0.35,
                    ease: [0.25, 0.46, 0.45, 0.94]
                  }}
                  onMouseEnter={(e) => handleTooltipShow(item.label, e)}
                  onMouseLeave={handleTooltipHide}
                  onFocus={(e) => handleTooltipShow(item.label, e)}
                  onBlur={handleTooltipHide}
                >
                  <SidebarMenuButton
                    active={active}
                    collapsed={collapsed}
                    icon={item.icon}
                    label={item.label}
                    expanded={isExpanded}
                    onClick={() => toggleExpand(item.label, item.href)}
                  />

                  <AnimatePresence initial={false}>
                    {isExpanded ? (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{
                          duration: 0.25,
                          ease: [0.4, 0, 0.2, 1],
                          opacity: { duration: 0.2 }
                        }}
                        className="ml-[3.15rem] mt-1 grid gap-0.5 overflow-hidden"
                      >
                        {item.children.map((child, childIndex) => (
                          <ChildNavLink
                            key={child.label}
                            child={child}
                            index={childIndex}
                            onClick={() => handleChildClick(child.href)}
                            isActive={activeChildHref === child.href || isHrefActive(child.href, currentHash)}
                          />
                        ))}
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </nav>

        <SidebarFooter collapsed={collapsed} />
      </motion.aside>

      {/* Render tooltips via portal to avoid clipping */}
      {typeof document !== 'undefined' && createPortal(
        <AnimatePresence>
          {collapsed && openTooltip ? (
            <CollapsedSubmenuPanel
              item={navItems.find(item => item.label === openTooltip) ?? fallbackNavItems[0]}
              open={true}
              position={tooltipPosition}
              currentHash={currentHash}
              onMouseEnter={() => {
                if (tooltipTimeoutRef.current) {
                  clearTimeout(tooltipTimeoutRef.current);
                }
              }}
              onMouseLeave={handleTooltipHide}
            />
          ) : null}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
}

function mapNavigationItem(item: NavigationItem): NavItem {
  return {
    label: item.label,
    href: item.href,
    icon: iconMap[item.icon] ?? LayoutDashboard,
    permission: item.permission,
    children: item.children.map((child) => ({
      label: child.label,
      href: child.href,
      icon: iconMap[child.icon] ?? Activity,
      permission: child.permission,
      badge: child.badge ?? undefined,
      badgeColor: child.badge_color ?? undefined
    }))
  };
}

function SidebarHeader({
  collapsed,
  mobile,
  onToggle
}: {
  collapsed: boolean;
  mobile: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={cn(
        "relative z-10 flex min-h-[52px] gap-2",
        collapsed ? "flex-col items-center justify-start" : "items-center justify-between"
      )}
    >
      <div className={cn("flex min-w-0 items-center gap-3", collapsed && "justify-center")}>
        <motion.div
          className="relative grid size-11 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-cyan-300 via-blue-400 to-violet-500 text-sm font-black text-white shadow-xl shadow-cyan-500/25"
          whileHover={{ scale: 1.08, rotate: 5 }}
          whileTap={{ scale: 0.94 }}
          aria-hidden
        >
          <span className="relative z-10">TA</span>
          <span className="absolute inset-0 rounded-xl bg-gradient-to-br from-white/30 via-white/10 to-transparent" />
          <span className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/20" />
          <motion.span
            className="absolute inset-0 rounded-xl bg-cyan-400/20"
            animate={{ opacity: [0, 0.5, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        </motion.div>

        <AnimatePresence initial={false} mode="wait">
          {!collapsed ? (
            <motion.div
              className="min-w-0 overflow-hidden"
              initial={{ opacity: 0, x: -12, width: 0 }}
              animate={{ opacity: 1, x: 0, width: "auto" }}
              exit={{ opacity: 0, x: -12, width: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
            >
              <p className="truncate text-sm font-black tracking-tight text-slate-900 dark:text-white">
                Trading AI
              </p>
              <p className="truncate text-xs font-semibold text-slate-500/80 dark:text-white/40">
                Research Console
              </p>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>

      <IconButton
        label={mobile ? "Close navigation" : collapsed ? "Expand sidebar" : "Collapse sidebar"}
        icon={mobile ? X : Menu}
        onClick={onToggle}
        className={cn(
          "relative z-10 shrink-0 transition-all duration-300",
          "hover:bg-white/10 hover:scale-105",
          collapsed ? "size-9" : "size-10"
        )}
      />
    </div>
  );
}

function SidebarMenuButton({
  active,
  collapsed,
  expanded,
  icon: Icon,
  label,
  onClick
}: {
  active?: boolean;
  collapsed: boolean;
  expanded: boolean;
  icon: LucideIcon;
  label: string;
  onClick: () => void;
}) {
  return (
    <motion.button
      type="button"
      aria-label={label}
      aria-expanded={collapsed ? undefined : expanded}
      title={collapsed ? label : undefined}
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.97 }}
      className={cn(
        "group relative flex min-h-11 w-full items-center gap-3 rounded-xl text-left text-sm font-semibold outline-none transition-all duration-300",
        collapsed ? "justify-center px-0" : "px-3",
        "text-slate-600 hover:bg-white/10 hover:text-slate-900",
        "dark:text-white/45 dark:hover:bg-white/[0.06] dark:hover:text-white",
        "hover:shadow-lg hover:shadow-black/5 dark:hover:shadow-black/20",
        active && cn(
          "bg-gradient-to-r from-cyan-400/25 via-cyan-400/15 to-cyan-400/5",
          "text-cyan-700 dark:text-cyan-100",
          "shadow-xl shadow-cyan-500/10 dark:shadow-cyan-500/20",
          "ring-1 ring-cyan-300/40 dark:ring-cyan-400/25"
        )
      )}
    >
      <motion.span
        className={cn(
          "grid size-9 shrink-0 place-items-center rounded-xl transition-all duration-300",
          "bg-white/10 text-slate-500 group-hover:bg-white/20",
          "dark:bg-white/[0.04] dark:text-white/45 dark:group-hover:bg-white/[0.08]",
          active && cn(
            "bg-gradient-to-br from-cyan-400/35 to-blue-400/30",
            "text-cyan-700 dark:text-cyan-200",
            "shadow-lg shadow-cyan-500/25 dark:shadow-cyan-500/30",
            "ring-1 ring-cyan-300/30 dark:ring-cyan-400/20"
          )
        )}
        whileHover={{ rotate: [0, -8, 8, 0] }}
        transition={{ duration: 0.4 }}
      >
        <Icon size={18} aria-hidden />
      </motion.span>

      <AnimatePresence mode="wait">
        {!collapsed ? (
          <motion.span
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="min-w-0 flex-1 truncate"
          >
            {label}
          </motion.span>
        ) : null}
      </AnimatePresence>

      {!collapsed ? (
        <motion.span
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
          className="text-slate-400/70 dark:text-white/25"
          aria-hidden
        >
          <ChevronDown size={16} />
        </motion.span>
      ) : null}

      {active && collapsed ? (
        <motion.span
          layoutId="activeIndicator"
          className="absolute right-1.5 top-1/2 size-2 -translate-y-1/2 rounded-full bg-cyan-400 shadow-lg shadow-cyan-400/60 dark:shadow-cyan-400/40"
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      ) : null}
    </motion.button>
  );
}

function CollapsedSubmenuPanel({
  item,
  open,
  position,
  currentHash,
  onMouseEnter,
  onMouseLeave
}: {
  item: NavItem;
  open: boolean;
  position: { top: number; left: number };
  currentHash: string;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}) {
  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          role="tooltip"
          initial={{ opacity: 0, scale: 0.94, x: -8 }}
          animate={{ opacity: 1, scale: 1, x: 0 }}
          exit={{ opacity: 0, scale: 0.94, x: -8 }}
          transition={{ duration: 0.2, ease: [0.4, 0, 0.2, 1] }}
          style={{
            position: 'fixed',
            top: position.top,
            left: position.left,
            zIndex: 9999,
          }}
          className="w-64"
          onMouseEnter={onMouseEnter}
          onMouseLeave={onMouseLeave}
        >
          <div
            className={cn(
              "overflow-hidden rounded-2xl border border-white/20",
              "bg-white/75 p-2.5 shadow-2xl shadow-slate-950/20 backdrop-blur-2xl",
              "dark:border-white/[0.08] dark:bg-slate-950/80 dark:shadow-black/40"
            )}
          >
            {/* Glass overlay */}
            <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-white/25 via-white/10 to-transparent dark:from-white/[0.08] dark:via-white/[0.03]" />
            <div className="relative z-10">
              <a
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-black outline-none transition-all duration-200",
                  "hover:bg-white/15 hover:shadow-md dark:hover:bg-white/[0.06]",
                  "focus-visible:ring-2 focus-visible:ring-cyan-300/70",
                  isNavItemActive(item, currentHash)
                    ? "text-cyan-700 dark:text-cyan-100 bg-cyan-400/10"
                    : "text-slate-900 dark:text-white"
                )}
                title={item.label}
              >
                <span className={cn(
                  "grid size-9 place-items-center rounded-xl transition-all",
                  "bg-gradient-to-br from-cyan-400/25 to-blue-400/20",
                  "text-cyan-700 shadow-lg shadow-cyan-500/10",
                  "dark:text-cyan-100 dark:shadow-cyan-500/20"
                )}>
                  <item.icon size={17} aria-hidden />
                </span>
                <span className="min-w-0 truncate">{item.label}</span>
              </a>

              {item.children.length > 0 ? (
                <div className="mt-1.5 grid gap-0.5 border-t border-white/10 dark:border-white/[0.06] pt-1.5">
                  {item.children.map((child, index) => (
                    <ChildNavLink key={child.label} child={child} index={index} panel isActive={isHrefActive(child.href, currentHash)} />
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

function ChildNavLink({
  child,
  index,
  panel = false,
  onClick,
  isActive = false
}: {
  child: ChildNavItem;
  index: number;
  panel?: boolean;
  onClick?: () => void;
  isActive?: boolean;
}) {
  return (
    <motion.a
      href={child.href}
      aria-label={child.label}
      title={child.label}
      onClick={onClick}
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04, duration: 0.25 }}
      whileHover={{ x: 4 }}
      className={cn(
        "group flex min-h-9 items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-semibold outline-none transition-all duration-200",
        "focus-visible:ring-2 focus-visible:ring-cyan-300/70 focus-visible:ring-offset-2",
        "text-slate-500 hover:bg-white/10 hover:text-slate-800",
        "dark:text-white/35 dark:hover:bg-white/[0.04] dark:hover:text-white/70",
        panel && "text-sm",
        (child.active || isActive) && cn(
          "bg-cyan-400/20 text-cyan-700 shadow-lg shadow-cyan-500/10",
          "ring-1 ring-cyan-300/30 dark:ring-cyan-400/25",
          "dark:text-cyan-100 dark:bg-cyan-400/15"
        ),
        "hover:shadow-md hover:shadow-black/5 dark:hover:shadow-black/20"
      )}
    >
      <child.icon
        size={13}
        className={cn(
          "shrink-0 transition-transform duration-200",
          "group-hover:scale-110"
        )}
        aria-hidden
      />
      <span className="min-w-0 flex-1 truncate">{child.label}</span>
      {child.badge ? (
        <motion.span
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: index * 0.04 + 0.1, type: "spring" }}
          className={cn(
            "rounded-lg px-1.5 py-0.5 text-[10px] font-bold backdrop-blur-sm",
            "ring-1 ring-inset ring-white/20 dark:ring-white/[0.08]",
            child.badgeColor ?? "bg-white/10 text-slate-600 dark:text-white/60"
          )}
        >
          {child.badge}
        </motion.span>
      ) : null}
    </motion.a>
  );
}

function SidebarFooter({ collapsed }: { collapsed: boolean }) {
  return (
    <div className="relative z-10 mt-auto grid gap-3">
      <AnimatePresence initial={false}>
        {!collapsed ? (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.95 }}
            transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
            className={cn(
              "rounded-xl border border-white/15 p-4 backdrop-blur-lg",
              "bg-gradient-to-br from-white/15 to-white/5",
              "dark:from-white/[0.06] dark:to-white/[0.02]",
              "dark:border-white/[0.06]",
              "shadow-xl shadow-black/5 dark:shadow-black/20"
            )}
          >
            <div className="flex items-center gap-2">
              <motion.div
                animate={{
                  rotate: [0, 15, -15, 0],
                  scale: [1, 1.1, 0.95, 1]
                }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              >
                <Zap size={16} className="text-amber-500" aria-hidden />
              </motion.div>
              <span className="text-xs font-bold text-slate-900 dark:text-white">
                Strategy Health
              </span>
            </div>

            <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/10 dark:bg-white/[0.04] ring-1 ring-inset ring-white/5">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: "78%" }}
                transition={{ duration: 1, delay: 0.3, ease: [0.4, 0, 0.2, 1] }}
                className="relative h-full rounded-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 shadow-lg shadow-emerald-500/25"
              >
                <div className="absolute inset-0 overflow-hidden rounded-full">
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                    animate={{ x: ["-100%", "100%"] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  />
                </div>
              </motion.div>
            </div>

            <div className="mt-2.5 flex items-center justify-between">
              <p className="text-xs font-semibold text-slate-500 dark:text-white/35">
                78% model coverage
              </p>
              <motion.span
                className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 }}
              >
                +2.4%
              </motion.span>
            </div>

            <div className="mt-3 grid grid-cols-2 gap-2">
              {[
                { label: "Signals", value: "24", color: "text-cyan-600 dark:text-cyan-400", bgColor: "bg-cyan-400/10 dark:bg-cyan-400/5" },
                { label: "Active", value: "6", color: "text-violet-600 dark:text-violet-400", bgColor: "bg-violet-400/10 dark:bg-violet-400/5" }
              ].map((stat, i) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.6 + i * 0.1 }}
                  className={cn(
                    "rounded-lg px-2 py-1.5 text-center backdrop-blur-sm",
                    "ring-1 ring-inset ring-white/10 dark:ring-white/[0.04]",
                    stat.bgColor
                  )}
                >
                  <p className={cn("text-sm font-bold", stat.color)}>{stat.value}</p>
                  <p className="text-[10px] font-semibold text-slate-500 dark:text-white/30">
                    {stat.label}
                  </p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <GlassLabelTooltip label="Settings" disabled={!collapsed}>
        <motion.a
          href="#/overview/settings"
          aria-label="Settings"
          title={collapsed ? "Settings" : undefined}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          className={cn(
            "flex min-h-11 items-center gap-3 rounded-xl text-sm font-semibold transition-all duration-300",
            collapsed ? "justify-center px-0" : "px-3",
            "text-slate-600 hover:bg-white/10 hover:text-slate-900",
            "dark:text-white/45 dark:hover:bg-white/[0.04] dark:hover:text-white",
            "hover:shadow-lg hover:shadow-black/5 dark:hover:shadow-black/20"
          )}
        >
          <motion.span
            className="grid size-9 place-items-center rounded-xl bg-white/10 dark:bg-white/[0.04]"
            whileHover={{ rotate: 90 }}
            transition={{ duration: 0.4 }}
          >
            <Settings size={18} aria-hidden />
          </motion.span>
          <AnimatePresence mode="wait">
            {!collapsed ? (
              <motion.span
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.15 }}
              >
                Settings
              </motion.span>
            ) : null}
          </AnimatePresence>
        </motion.a>
      </GlassLabelTooltip>
    </div>
  );
}

function GlassLabelTooltip({
  label,
  children,
  disabled = false
}: {
  label: string;
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <div className="group/tooltip relative">
      {children}
      {!disabled ? (
        <span className={cn(
          "pointer-events-none absolute left-[calc(100%+12px)] top-1/2 z-[9999]",
          "whitespace-nowrap rounded-xl px-3 py-2 text-xs font-bold backdrop-blur-xl",
          "border border-white/20 bg-white/75 text-slate-900 shadow-2xl shadow-slate-950/20",
          "dark:border-white/[0.08] dark:bg-slate-950/80 dark:text-white dark:shadow-black/40",
          "opacity-0 transition-all duration-200",
          "-translate-y-1/2 translate-x-2",
          "group-hover/tooltip:translate-x-0 group-hover/tooltip:opacity-100",
          "group-focus-within/tooltip:translate-x-0 group-focus-within/tooltip:opacity-100"
        )}>
          {label}
        </span>
      ) : null}
    </div>
  );
}

function isNavItemActive(item: NavItem, currentHash: string) {
  return Boolean(item.active || isHrefActive(item.href, currentHash) || item.children.some((child) => child.active || isHrefActive(child.href, currentHash)));
}

function isHrefActive(href: string, currentHash: string) {
  const normalizedCurrent = currentHash || "#/overview";
  return normalizedCurrent === href || normalizedCurrent.startsWith(`${href}/`);
}
