import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#F8F9FA",
        surface: "#FFFFFF",
        border: "#DEE2E6",
        primary: "#1B3A6B",
        accent: "#DC2626",
        "stock-up": "#DC2626",
        "stock-down": "#1565C0",
        "text-primary": "#1A1A1A",
        "text-secondary": "#4A5568",
        "text-muted": "#868E96",
        "header-bg": "#0D1B3E",
      },
    },
  },
  plugins: [],
};

export default config;
