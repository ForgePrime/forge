import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      spacing: {
        "topnav": "var(--topnav-height)",
        "left-panel": "var(--left-panel-width)",
        "right-sidebar": "var(--right-sidebar-width)",
        "right-sidebar-collapsed": "var(--right-sidebar-collapsed-width)",
      },
      keyframes: {
        "slide-in-right": {
          from: { transform: "translateX(100%)" },
          to: { transform: "translateX(0)" },
        },
      },
      animation: {
        "slide-in-right": "slide-in-right 0.2s ease-out",
      },
      colors: {
        forge: {
          50: "#f0f4ff",
          100: "#dbe4ff",
          200: "#bac8ff",
          300: "#91a7ff",
          400: "#748ffc",
          500: "#5c7cfa",
          600: "#4c6ef5",
          700: "#4263eb",
          800: "#3b5bdb",
          900: "#364fc7",
        },
      },
    },
  },
  plugins: [],
};

export default config;
