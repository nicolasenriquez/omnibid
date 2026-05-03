import type { CSSProperties, HTMLAttributes } from "react";

import { cn } from "@/src/lib/cn";

type SkeletonProps = HTMLAttributes<HTMLDivElement> & {
  height?: string;
};

export function Skeleton({ className, style, height, ...props }: SkeletonProps) {
  const merged: CSSProperties = {
    ...style,
    height: height ?? style?.height ?? "1rem",
  };

  return <div className={cn("ui-skeleton", className)} style={merged} {...props} />;
}
