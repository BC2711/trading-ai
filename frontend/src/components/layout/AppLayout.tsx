import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";

import { Footer } from "./Footer";
import { Navbar } from "./Navbar";
import { Sidebar } from "./Sidebar";

type AppLayoutProps = {
  children: ReactNode;
};

export function AppLayout({ children }: AppLayoutProps) {
  const [isDark, setIsDark] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const shellClassName = useMemo(() => (isDark ? "dark" : ""), [isDark]);

  return (
    <div className={shellClassName}>
      <div className="min-h-screen bg-[linear-gradient(135deg,#eef7f4_0%,#f5f2ff_42%,#f8fafc_100%)] text-slate-950 transition-colors duration-500 dark:bg-[linear-gradient(135deg,#071016_0%,#111827_46%,#18112a_100%)] dark:text-white">
        <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_15%_12%,rgba(34,211,238,0.22),transparent_30%),radial-gradient(circle_at_83%_8%,rgba(168,85,247,0.18),transparent_28%),radial-gradient(circle_at_60%_88%,rgba(16,185,129,0.14),transparent_34%)]" />

        <div className="relative mx-auto grid min-h-screen w-full max-w-[1800px] grid-cols-1 gap-4 p-3 lg:grid-cols-[auto_minmax(0,1fr)] lg:p-4 xl:p-6">
          <aside className="sticky top-4 hidden h-[calc(100vh-2rem)] lg:block xl:top-6 xl:h-[calc(100vh-3rem)]">
            <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((value) => !value)} />
          </aside>

          <AnimatePresence>
            {mobileOpen ? (
              <motion.div
                className="fixed inset-0 z-50 bg-slate-950/40 p-3 backdrop-blur-lg lg:hidden"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onMouseDown={() => setMobileOpen(false)}
              >
                <motion.div
                  initial={{ x: -24, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  exit={{ x: -24, opacity: 0 }}
                  onMouseDown={(event) => event.stopPropagation()}
                >
                  <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} mobile />
                </motion.div>
              </motion.div>
            ) : null}
          </AnimatePresence>

          <div className="grid min-w-0 grid-rows-[auto_1fr_auto] gap-4">
            <Navbar isDark={isDark} onThemeToggle={() => setIsDark((value) => !value)} onMobileMenu={() => setMobileOpen(true)} />
            <main className="min-w-0">{children}</main>
            <Footer />
          </div>
        </div>
      </div>
    </div>
  );
}
