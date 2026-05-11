import { Card } from "@/src/components/ui";

export default function LicitacionesLoading() {
  return (
    <main aria-busy="true" className="route-state">
      <Card className="route-state__content">
        <p className="route-state__eyebrow">Licitaciones</p>
        <h1 className="route-state__title">Cargando espacio de oportunidades...</h1>
        <p className="route-state__description" aria-live="polite">
          Estamos preparando la vista para que puedas revisar oportunidades.
        </p>
      </Card>
    </main>
  );
}
