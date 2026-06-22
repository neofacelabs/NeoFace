import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          0: "#000000",
          1: "#030303",
          2: "#050505",
          3: "#0a0a0a",
          4: "#111111",
        },
        surface: {
          1: "rgba(255,255,255,0.028)",
          2: "rgba(255,255,255,0.055)",
          3: "rgba(255,255,255,0.085)",
          4: "rgba(255,255,255,0.12)",
        },
        border: {
          1: "rgba(255,255,255,0.055)",
          2: "rgba(255,255,255,0.10)",
          3: "rgba(255,255,255,0.18)",
        },
        text: {
          primary:   "#ffffff",
          secondary: "rgba(255,255,255,0.50)",
          tertiary:  "rgba(255,255,255,0.28)",
          subtle:    "rgba(255,255,255,0.16)",
        },
        accent: {
          DEFAULT: "#0EA5E9",
          dim:     "rgba(14,165,233,0.08)",
          glow:    "rgba(14,165,233,0.20)",
          soft:    "#38BDF8",
          deep:    "#0284C7",
          muted:   "#7DD3FC",
        },
        emerald: "#00E5A8",
        teal:    "#14B8A6",
        cyan:    "#00C2FF",
        sky:     "#38BDF8",
        mint:    "#00FFD1",
        success: "#00E5A8",
        error:   "#f87171",
        warning: "#fbbf24",
        // shadcn compat
        background:  "#000000",
        foreground:  "#ffffff",
        card:        { DEFAULT: "rgba(255,255,255,0.025)", foreground: "#ffffff" },
        popover:     { DEFAULT: "#0a0a0a",                 foreground: "#ffffff" },
        primary:     { DEFAULT: "#00E5A8",                 foreground: "#000000" },
        secondary:   { DEFAULT: "#14F1D9",                 foreground: "#000000" },
        muted:       { DEFAULT: "#0a0a0a",                 foreground: "rgba(255,255,255,0.35)" },
        destructive: { DEFAULT: "#f87171",                 foreground: "#ffffff" },
        ring:  "#00E5A8",
        input: "rgba(255,255,255,0.06)",
      },

      fontFamily: {
        sans:    ["var(--font-geist-sans)", "Inter Tight", "Inter", "system-ui", "sans-serif"],
        mono:    ["var(--font-geist-mono)", "Fira Code", "monospace"],
        display: ["var(--font-geist-sans)", "Inter Tight", "system-ui", "sans-serif"],
      },

      fontSize: {
        // Display-level sizes (landing hero)
        "display":  ["clamp(4.5rem, 12vw, 9rem)",   { lineHeight: "0.93", letterSpacing: "-0.04em",  fontWeight: "700" }],
        "hero":     ["clamp(3rem, 8vw, 6.5rem)",     { lineHeight: "0.96", letterSpacing: "-0.035em", fontWeight: "700" }],
        "title-1":  ["clamp(2rem, 5vw, 4rem)",       { lineHeight: "1.0",  letterSpacing: "-0.03em",  fontWeight: "700" }],
        "title-2":  ["clamp(1.5rem, 3.5vw, 2.5rem)", { lineHeight: "1.06", letterSpacing: "-0.025em", fontWeight: "600" }],
        "title-3":  ["clamp(1.125rem, 2vw, 1.75rem)", { lineHeight: "1.15", letterSpacing: "-0.02em",  fontWeight: "600" }],
      },

      borderRadius: {
        "4xl": "2rem",
        "5xl": "2.5rem",
        "6xl": "3rem",
      },

      backgroundImage: {
        "gradient-radial":  "radial-gradient(var(--tw-gradient-stops))",
        "glow-accent":      "radial-gradient(ellipse 600px 400px at 50% 0%, rgba(0,229,168,0.1) 0%, transparent 70%)",
        "glow-center":      "radial-gradient(ellipse 800px 600px at 50% 50%, rgba(0,229,168,0.06) 0%, transparent 70%)",
        "card-shine":       "linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)",
        "divider":          "linear-gradient(90deg, transparent 0%, rgba(0,229,168,0.08) 30%, rgba(0,194,255,0.06) 70%, transparent 100%)",
      },

      boxShadow: {
        "glow-xs":    "0 0 12px rgba(0,229,168,0.10)",
        "glow-sm":    "0 0 24px rgba(0,229,168,0.13)",
        "glow-md":    "0 0 48px rgba(0,229,168,0.16)",
        "glow-lg":    "0 0 80px rgba(0,229,168,0.21)",
        "glow-cyan":  "0 0 32px rgba(14,165,233,0.13)",
        "glow-white": "0 0 32px rgba(255,255,255,0.12)",
        "card":       "0 1px 0 rgba(255,255,255,0.04), 0 4px 24px rgba(0,0,0,0.6)",
        "card-hover": "0 1px 0 rgba(255,255,255,0.07), 0 8px 40px rgba(0,0,0,0.7)",
        "modal":      "0 0 0 1px rgba(255,255,255,0.08), 0 24px 80px rgba(0,0,0,0.8)",
        "button":     "0 1px 0 rgba(255,255,255,0.08) inset, 0 0 20px rgba(0,229,168,0.09)",
      },

      animation: {
        "fade-up":       "fade-up 0.7s cubic-bezier(0.16,1,0.3,1) both",
        "fade-in":       "fade-in 0.6s ease both",
        "float":         "float-y 5s ease-in-out infinite",
        "float-slow":    "float-y-slow 8s ease-in-out infinite",
        "pulse-ring":    "pulse-ring 2.2s cubic-bezier(0,0,0.2,1) infinite",
        "spin-slow":     "spin-slow 18s linear infinite",
        "spin-slow-ccw": "spin-slow-ccw 24s linear infinite",
        "scan":          "scan-down 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "shimmer":       "shimmer 4s linear infinite",
        "neural":        "neural-pulse 3s ease-in-out infinite",
        "dash":          "dash-flow 1.2s linear infinite",
        "iris-cw":       "iris-rotate-cw 12s linear infinite",
        "iris-ccw":      "iris-rotate-ccw 18s linear infinite",
        "mesh-pulse":    "mesh-pulse 3.5s ease-in-out infinite",
        "count-reveal":  "count-reveal 0.8s cubic-bezier(0.16,1,0.3,1) both",
      },

      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(24px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        "float-y": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-12px)" },
        },
        "float-y-slow": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%":      { transform: "translateY(-20px)" },
        },
        "pulse-ring": {
          "0%":   { transform: "scale(1)",   opacity: "0.6" },
          "100%": { transform: "scale(2.2)", opacity: "0" },
        },
        "spin-slow": {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(360deg)" },
        },
        "spin-slow-ccw": {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(-360deg)" },
        },
        "scan-down": {
          "0%":   { transform: "translateY(-100%)", opacity: "0" },
          "5%":   { opacity: "1" },
          "95%":  { opacity: "1" },
          "100%": { transform: "translateY(400%)", opacity: "0" },
        },
        "neural-pulse": {
          "0%, 100%": { opacity: "0.2", transform: "scale(0.95)" },
          "50%":      { opacity: "0.8", transform: "scale(1.05)" },
        },
        "shimmer": {
          "0%":   { backgroundPosition: "-200% center" },
          "100%": { backgroundPosition: "200% center" },
        },
        "iris-rotate-cw": {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(360deg)" },
        },
        "iris-rotate-ccw": {
          from: { transform: "rotate(0deg)" },
          to:   { transform: "rotate(-360deg)" },
        },
        "dash-flow": {
          to: { strokeDashoffset: "-40" },
        },
        "mesh-pulse": {
          "0%, 100%": { opacity: "0.25" },
          "50%":      { opacity: "0.65" },
        },
        "count-reveal": {
          from: { opacity: "0", transform: "translateY(10px) scale(0.95)" },
          to:   { opacity: "1", transform: "translateY(0) scale(1)" },
        },
      },
    },
  },
  plugins: [typography],
};

export default config;
