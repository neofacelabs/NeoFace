"use client";
import { motion } from "framer-motion";
import { Shield, TrendingUp, Zap } from "lucide-react";
import { cn } from "@/lib/utils";

interface FloatingCardProps {
  label: string;
  value: string;
  variant?: "success" | "indigo" | "purple";
  icon?: "shield" | "trend" | "zap";
  className?: string;
  delay?: number;
}

const ICONS = { shield: Shield, trend: TrendingUp, zap: Zap };
const COLORS = {
  success: { bg: "bg-success/10", border: "border-success/20", text: "text-success", dot: "bg-success" },
  indigo: { bg: "bg-accent-violet/10", border: "border-accent-violet/20", text: "text-accent-soft", dot: "bg-accent-violet" },
  purple: { bg: "bg-purple-500/10", border: "border-purple-500/20", text: "text-purple-400", dot: "bg-purple-500" },
};

export function FloatingCard({ label, value, variant = "indigo", icon, className, delay = 0 }: FloatingCardProps) {
  const color = COLORS[variant];
  const Icon = icon ? ICONS[icon] : null;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ scale: 1.05, y: -2 }}
      className={cn(
        "glass rounded-xl px-3 py-2.5 shadow-card min-w-[130px]",
        "border",
        color.border,
        className
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <motion.div
          className={cn("w-1.5 h-1.5 rounded-full", color.dot)}
          animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
        <span className="text-xs text-text-muted">{label}</span>
        {Icon && <Icon className={cn("w-3 h-3 ml-auto", color.text)} />}
      </div>
      <div className={cn("text-base font-bold", color.text)}>{value}</div>
    </motion.div>
  );
}
