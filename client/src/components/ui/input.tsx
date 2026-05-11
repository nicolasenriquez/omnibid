import type { ComponentProps } from "react";

import { cn } from "@/src/lib/cn";

type InputProps = ComponentProps<"input">;

export function Input({ className, ref, ...props }: InputProps) {
  return <input ref={ref} className={cn("ui-input", className)} {...props} />;
}
