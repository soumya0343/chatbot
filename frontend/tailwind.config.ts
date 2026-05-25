import type { Config } from "tailwindcss";

function hsl(v: string) {
  return `hsl(var(${v}))`;
}

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: hsl("--background"),
        foreground: hsl("--foreground"),
        card: { DEFAULT: hsl("--card"), foreground: hsl("--card-foreground") },
        popover: { DEFAULT: hsl("--popover"), foreground: hsl("--popover-foreground") },
        primary: { DEFAULT: hsl("--primary"), foreground: hsl("--primary-foreground") },
        secondary: { DEFAULT: hsl("--secondary"), foreground: hsl("--secondary-foreground") },
        muted: { DEFAULT: hsl("--muted"), foreground: hsl("--muted-foreground") },
        accent: { DEFAULT: hsl("--accent"), foreground: hsl("--accent-foreground") },
        destructive: { DEFAULT: hsl("--destructive"), foreground: hsl("--destructive-foreground") },
        border: hsl("--border"),
        input: hsl("--input"),
        ring: hsl("--ring"),
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
