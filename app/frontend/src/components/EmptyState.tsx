import type { ReactNode } from "react";

export function EmptyState({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-slate-200 py-8 text-center text-sm text-slate-400">
      {icon}
      <span>{children}</span>
    </div>
  );
}
