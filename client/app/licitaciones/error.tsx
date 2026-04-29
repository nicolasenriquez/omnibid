"use client";

type LicitacionesErrorProps = {
  error: Error;
  reset: () => void;
};

export default function LicitacionesError({ error, reset }: LicitacionesErrorProps) {
  return (
    <main style={{ padding: "1.5rem 2rem" }}>
      <h1 style={{ marginTop: 0, fontSize: "1.25rem" }}>Error en licitaciones</h1>
      <p style={{ color: "#475569" }}>
        No se pudo abrir el espacio de oportunidades. {error.message}
      </p>
      <button
        onClick={reset}
        type="button"
        style={{
          border: "1px solid #94a3b8",
          borderRadius: "6px",
          background: "#ffffff",
          color: "#0f172a",
          padding: "0.5rem 0.75rem",
          cursor: "pointer",
        }}
      >
        Reintentar
      </button>
    </main>
  );
}
