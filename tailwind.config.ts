import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0A0A0F",
        surface: "#1A1A2E",
        border: "#2A2A4A",
        primary: "#7C3AED",
        accent: "#F59E0B",
      },
    },
  },
  plugins: [],
};

export default config;
