"use client";
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all duration-200 disabled:pointer-events-none disabled:opacity-40 select-none cursor-pointer",
  {
    variants: {
      variant: {
        // Primary: glass white
        default:
          "btn-primary rounded-xl text-white",
        // Accent: indigo-ish glow
        accent:
          "btn-accent rounded-xl text-white font-semibold",
        // Ghost: minimal
        ghost:
          "text-[rgba(255,255,255,0.5)] hover:text-white hover:bg-[rgba(255,255,255,0.05)] rounded-xl transition-colors",
        // Outline
        outline:
          "border border-[rgba(255,255,255,0.08)] text-[rgba(255,255,255,0.55)] hover:border-[rgba(255,255,255,0.16)] hover:text-white hover:bg-[rgba(255,255,255,0.04)] rounded-xl transition-all",
        // Danger
        danger:
          "bg-[rgba(248,113,113,0.1)] border border-[rgba(248,113,113,0.2)] text-[#f87171] hover:bg-[rgba(248,113,113,0.18)] rounded-xl",
        // Link
        link:
          "text-accent-soft underline-offset-4 hover:underline p-0 h-auto rounded-none",
      },
      size: {
        xs:    "h-7 px-3 text-xs rounded-lg",
        sm:    "h-8 px-3.5 text-xs",
        default: "h-10 px-4",
        lg:    "h-11 px-5 text-sm",
        xl:    "h-12 px-6 text-sm",
        "2xl": "h-14 px-8 text-base",
        icon:     "h-10 w-10",
        "icon-sm":"h-8  w-8 rounded-lg",
        "icon-xs":"h-7  w-7 rounded-md",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={loading || disabled}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-3.5 w-3.5 shrink-0" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {children}
    </button>
  )
);
Button.displayName = "Button";

export { Button, buttonVariants };
