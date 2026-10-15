import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: "#1A3764",
        blue: "#1567A9",
        teal: "#31A8E0",
        green: "#3AAA35",
        lime: "#94C11F",
        ink: "#3D3D3C",
        surface: "#F5F8FA",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "8px",
      },
    },
  },
  plugins: [],
} satisfies Config;
