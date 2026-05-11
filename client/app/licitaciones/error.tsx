"use client";

import { Button, Card } from "@/src/components/ui";

type LicitacionesErrorProps = {
  error: Error;
  reset: () => void;
};

export default function LicitacionesError({ error, reset }: LicitacionesErrorProps) {
  return (
    <main className="route-state">
      <Card className="route-state__content">
        <p className="route-state__eyebrow">Licitaciones</p>
        <h1 className="route-state__title">Error en licitaciones</h1>
        <p className="route-state__description">
          No se pudo abrir el espacio de oportunidades. {error.message}
        </p>
        <div className="route-state__actions">
          <Button onClick={reset} variant="primary" type="button">
            Reintentar
          </Button>
        </div>
      </Card>
    </main>
  );
}
