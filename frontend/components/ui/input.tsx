import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  icon?: React.ReactNode;
  suffix?: React.ReactNode;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, icon, suffix, type, ...props }, ref) => (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-xs font-medium text-[rgba(255,255,255,0.45)] tracking-wide uppercase">
          {label}
        </label>
      )}
      <div
        className={cn(
          "relative flex items-center rounded-xl border transition-all duration-200",
          "bg-[rgba(255,255,255,0.03)] border-[rgba(255,255,255,0.08)]",
          "focus-within:bg-[rgba(255,255,255,0.05)] focus-within:border-[rgba(255,255,255,0.15)]",
          "focus-within:ring-2 focus-within:ring-[rgba(124,124,255,0.12)]",
          error && "border-[rgba(248,113,113,0.35)] focus-within:border-[rgba(248,113,113,0.5)] focus-within:ring-[rgba(248,113,113,0.1)]"
        )}
      >
        {icon && (
          <div className="absolute left-3.5 text-[rgba(255,255,255,0.3)] pointer-events-none">
            {icon}
          </div>
        )}
        <input
          type={type}
          ref={ref}
          className={cn(
            "flex-1 h-11 bg-transparent text-sm text-white placeholder:text-[rgba(255,255,255,0.22)] outline-none px-3.5",
            icon && "pl-10",
            suffix && "pr-10",
            className
          )}
          {...props}
        />
        {suffix && (
          <div className="absolute right-3.5 text-[rgba(255,255,255,0.3)]">
            {suffix}
          </div>
        )}
      </div>
      {error && <p className="text-xs text-[#f87171]">{error}</p>}
      {hint && !error && <p className="text-xs text-[rgba(255,255,255,0.28)]">{hint}</p>}
    </div>
  )
);
Input.displayName = "Input";

export { Input };
