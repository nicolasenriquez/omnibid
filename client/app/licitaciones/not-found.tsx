import { Card } from "@/src/components/ui";

export default function LicitacionesNotFound() {
  return (
    <main className="route-state">
      <Card className="route-state__content">
        <p className="route-state__eyebrow">Licitaciones</p>
        <h1 className="route-state__title">No encontrado</h1>
        <p className="route-state__description">
          La vista solicitada no existe dentro del espacio de licitaciones.
        </p>
      </Card>
    </main>
  );
}
