import { forwardRef } from "react";
import type { SelectHTMLAttributes } from "react";

import { cn } from "@/src/lib/cn";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, children, ...props },
  ref,
) {
  return (
    <select ref={ref} className={cn("ui-select", className)} {...props}>
      {children}
    </select>
  );
});
