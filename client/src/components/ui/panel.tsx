import type { HTMLAttributes } from "react";

import { cn } from "@/src/lib/cn";

type PanelProps = HTMLAttributes<HTMLDivElement> & {
  dense?: boolean;
};

export function Panel({ dense = false, className, ...props }: PanelProps) {
  return <div className={cn("ui-panel", dense ? "ui-panel--dense" : null, className)} {...props} />;
}
