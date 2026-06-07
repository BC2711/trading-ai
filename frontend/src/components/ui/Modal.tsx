import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import type { ReactNode } from "react";

import { IconButton } from "./Button";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function Modal({ open, onClose, title, children, footer }: ModalProps) {
  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 p-4 backdrop-blur-lg"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          onMouseDown={onClose}
        >
          <motion.div
            className="w-full max-w-xl rounded-[8px] border border-white/20 bg-white/70 shadow-2xl shadow-slate-950/30 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/75"
            initial={{ opacity: 0, y: 24, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.97 }}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-white/10 p-5">
              <h2 id="modal-title" className="text-lg font-bold text-slate-950 dark:text-white">
                {title}
              </h2>
              <IconButton label="Close modal" icon={X} onClick={onClose} />
            </div>
            <div className="p-5">{children}</div>
            {footer ? <div className="flex justify-end gap-2 border-t border-white/10 p-5">{footer}</div> : null}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
