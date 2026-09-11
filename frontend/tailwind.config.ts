import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        civic: {
          50: "#ecfeff",
          400: "#22d3ee",
          500: "#06b6d4",
          700: "#0e7490",
          900: "#083344",
          950: "#051822",
        },
        moss: { 400: "#4ade80", 600: "#16a34a" },
      },
      fontFamily: {
        sans: ["DM Sans", "Segoe UI", "system-ui", "sans-serif"],
        display: ["Outfit", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        glass: "0 8px 40px rgba(6, 182, 212, 0.12)",
      },
    },
  },
  plugins: [],
} satisfies Config;
