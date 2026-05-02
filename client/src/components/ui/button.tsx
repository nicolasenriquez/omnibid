import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

import { cn } from "@/src/lib/cn";

type Variant = "primary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
  busy?: boolean;
  leadingIcon?: ReactNode;
  trailingIcon?: ReactNode;
};

export function Button({
  className,
  children,
  variant = "ghost",
  loading = false,
  busy = false,
  leadingIcon,
  trailingIcon,
  disabled,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "ui-button",
        variant === "primary" ? "ui-button--primary" : "ui-button--ghost",
        busy && "ui-button--busy",
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || busy || undefined}
      type={type}
      {...props}
    >
      {loading ? <Loader2 size={15} aria-hidden="true" /> : leadingIcon}
      <span>{children}</span>
      {!loading && trailingIcon ? <span className="ui-button__trailing">{trailingIcon}</span> : null}
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
