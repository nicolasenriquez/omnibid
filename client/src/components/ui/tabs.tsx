import type { ReactNode } from "react";

import { cn } from "@/src/lib/cn";

export type TabOption<T extends string> = {
  id: T;
  label: string;
  suffix?: ReactNode;
};

type TabsProps<T extends string> = {
  label: string;
  value: T;
  options: TabOption<T>[];
  onChange: (value: T) => void;
};

export function Tabs<T extends string>({ label, value, options, onChange }: TabsProps<T>) {
  return (
    <div role="tablist" aria-label={label} className="ui-tabs">
      {options.map((option) => (
        <button
          key={option.id}
          role="tab"
          type="button"
          aria-selected={value === option.id}
          className={cn("ui-tab")}
          onClick={() => onChange(option.id)}
        >
          <span>{option.label}</span>
          {option.suffix}
        </button>
      ))}
    </div>
  );
}
