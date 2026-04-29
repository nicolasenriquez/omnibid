import type { ReactNode } from "react";

import { cn } from "@/src/lib/cn";

type BadgeProps = {
  children: ReactNode;
  className?: string;
};

export function Badge({ children, className }: BadgeProps) {
  return <span className={cn("ui-badge", className)}>{children}</span>;
}
