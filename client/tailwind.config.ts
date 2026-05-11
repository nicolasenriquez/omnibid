import type { Config } from "tailwindcss";

const config = {
  content: ["./app/**/*.{ts,tsx,mdx}", "./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: {
          app: "var(--background-app)",
          surface: "var(--background-surface)",
          subtle: "var(--background-subtle)",
          elevated: "var(--background-elevated)",
          hover: "var(--background-hover)",
          tableHead: "var(--background-table-head)",
          selectedRow: "var(--background-selected-row)",
        },
        border: {
          subtle: "var(--border-subtle)",
          strong: "var(--border-strong)",
        },
        text: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-muted)",
          inverse: "var(--text-inverse)",
        },
        brand: {
          primary: "var(--accent)",
          hover: "var(--accent-hover)",
          soft: "var(--accent-soft)",
          border: "var(--accent-border)",
        },
        selection: {
          bg: "var(--selection-bg)",
          border: "var(--selection-border)",
        },
        status: {
          open: "var(--status-open)",
          openBg: "var(--status-open-bg)",
          closingSoon: "var(--status-closing-soon)",
          closingSoonBg: "var(--status-closing-soon-bg)",
          closed: "var(--status-closed)",
          closedBg: "var(--status-closed-bg)",
          awarded: "var(--status-awarded)",
          awardedBg: "var(--status-awarded-bg)",
          risk: "var(--status-risk)",
          riskBg: "var(--status-risk-bg)",
        },
      },
      fontFamily: {
        sans: ["var(--font-family-sans)"],
        mono: ["var(--font-family-mono)"],
      },
      spacing: {
        1: "var(--space-1)",
        2: "var(--space-2)",
        3: "var(--space-3)",
        4: "var(--space-4)",
        5: "var(--space-5)",
        6: "var(--space-6)",
        8: "var(--space-8)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        pill: "var(--radius-pill)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        cardHover: "var(--shadow-card-hover)",
        table: "var(--shadow-table)",
        surfaceStrong: "var(--shadow-surface-strong)",
        panel: "var(--shadow-panel)",
        popover: "var(--shadow-popover)",
      },
      transitionDuration: {
        fast: "var(--motion-duration-fast)",
        medium: "var(--motion-duration-medium)",
        slow: "var(--motion-duration-slow)",
      },
      transitionTimingFunction: {
        standard: "var(--motion-ease-standard)",
        emphasized: "var(--motion-ease-emphasized)",
      },
    },
  },
} satisfies Config;

export default config;
