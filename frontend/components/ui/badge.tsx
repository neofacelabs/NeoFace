import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default:  "bg-[rgba(124,124,255,0.12)] text-[#a5b4fc] border border-[rgba(124,124,255,0.2)]",
        success:  "bg-[rgba(52,211,153,0.1)]   text-[#34d399] border border-[rgba(52,211,153,0.2)]",
        error:    "bg-[rgba(248,113,113,0.1)]  text-[#f87171] border border-[rgba(248,113,113,0.2)]",
        warning:  "bg-[rgba(251,191,36,0.1)]   text-[#fbbf24] border border-[rgba(251,191,36,0.2)]",
        ghost:    "bg-[rgba(255,255,255,0.04)]  text-[rgba(255,255,255,0.4)] border border-[rgba(255,255,255,0.07)]",
        outline:  "border border-[rgba(255,255,255,0.10)] text-[rgba(255,255,255,0.45)]",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
