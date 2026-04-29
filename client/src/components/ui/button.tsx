import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/src/lib/cn";

type Variant = "primary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
  leadingIcon?: ReactNode;
};

export function Button({
  className,
  children,
  variant = "ghost",
  loading = false,
  leadingIcon,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "ui-button",
        variant === "primary" ? "ui-button--primary" : "ui-button--ghost",
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      type={type}
      {...props}
    >
      {loading ? <Loader2 size={15} aria-hidden="true" /> : leadingIcon}
      <span>{children}</span>
    </button>
  );
}

type IconButtonProps = Omit<ButtonProps, "children" | "leadingIcon"> & {
  icon: ReactNode;
  label: string;
};

export function IconButton({ icon, label, className, ...props }: IconButtonProps) {
  return (
    <button
      className={cn("ui-icon-button", className)}
      aria-label={label}
      type="button"
      {...props}
    >
      {icon}
    </button>
  );
}
