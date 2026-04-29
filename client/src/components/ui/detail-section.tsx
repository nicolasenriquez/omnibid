import type { ReactNode } from "react";

type DetailSectionProps = {
  title: string;
  children: ReactNode;
};

export function DetailSection({ title, children }: DetailSectionProps) {
  return (
    <section className="detail-section">
      <h3 className="detail-section__title">{title}</h3>
      <div className="detail-section__body">{children}</div>
    </section>
  );
}
