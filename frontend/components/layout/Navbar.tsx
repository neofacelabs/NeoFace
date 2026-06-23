"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";

const NAV = [
  { label: "Features",    href: "#product" },
  { label: "Developers",  href: "#developers" },
  { label: "Security",    href: "#security" },
  { label: "Pricing",     href: "/pricing" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const { isAuthenticated, user } = useAuthStore();
  const isDashboard = pathname.startsWith("/dashboard");

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  if (isDashboard) return null;

  return (
    <>
      <motion.header
        initial={{ y: -12, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className={cn(
          "fixed top-0 inset-x-0 z-50 transition-all duration-500",
          scrolled
            ? "border-b border-[rgba(255,255,255,0.055)] backdrop-blur-2xl bg-[rgba(0,0,0,0.80)]"
            : "bg-transparent"
        )}
      >
        <div className="max-w-7xl mx-auto px-6 h-[64px] flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <motion.div whileHover={{ scale: 1.02 }} transition={{ duration: 0.3 }}>
              <Image src="/logo.png" alt="NeoFace Logo" width={200} height={60} className="h-12 w-auto object-contain" />
            </motion.div>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-0.5">
            {NAV.map((item) => (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "px-4 py-2 text-[13px] rounded-lg hover:bg-[rgba(255,255,255,0.04)] transition-all duration-150 font-medium tracking-[-0.01em]",
                  item.label === "Pricing"
                    ? "text-[#00E5A8]/80 hover:text-[#00E5A8]"
                    : "text-[rgba(255,255,255,0.42)] hover:text-white"
                )}
              >
                {item.label}
              </Link>
            ))}
          </nav>

          {/* CTA */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <Link href="/dashboard">
                  <button className="px-4 py-2 text-[13px] text-[rgba(255,255,255,0.5)] hover:text-white transition-colors font-medium">
                    Dashboard
                  </button>
                </Link>
                <div className="w-7 h-7 rounded-full bg-[rgba(0,229,168,0.1)] border border-[rgba(0,229,168,0.25)] flex items-center justify-center text-xs font-semibold text-[#00E5A8]">
                  {user?.name?.[0]?.toUpperCase() ?? "U"}
                </div>
              </>
            ) : (
              <>
                <Link href="/login">
                  <button className="px-4 py-2 text-[13px] text-[rgba(255,255,255,0.45)] hover:text-white transition-colors font-medium">
                    Log in
                  </button>
                </Link>
                <Link href="/register">
                  <motion.button
                    whileHover={{ scale: 1.02, boxShadow: "0 0 20px rgba(0,229,168,0.3)" }}
                    whileTap={{ scale: 0.98 }}
                    className="px-5 py-2 text-[13px] rounded-full font-semibold bg-[#00E5A8] text-black"
                  >
                    Get API Key
                  </motion.button>
                </Link>
              </>
            )}
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setOpen(!open)}
            className="md:hidden p-2 rounded-lg text-[rgba(255,255,255,0.5)] hover:text-white hover:bg-[rgba(255,255,255,0.05)] transition-colors"
          >
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </motion.header>

      {/* Mobile drawer */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
            className="fixed top-[64px] inset-x-0 z-40 border-b border-[rgba(255,255,255,0.06)] bg-[rgba(0,0,0,0.95)] backdrop-blur-2xl md:hidden"
          >
            <nav className="px-5 py-4 flex flex-col gap-0.5">
              {NAV.map((item) => (
                <Link
                  key={item.label}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "px-3 py-3 text-sm rounded-xl hover:bg-[rgba(255,255,255,0.04)] transition-all font-medium",
                    item.label === "Pricing"
                      ? "text-[#00E5A8]/70 hover:text-[#00E5A8]"
                      : "text-[rgba(255,255,255,0.55)] hover:text-white"
                  )}
                >
                  {item.label}
                </Link>
              ))}
              <div className="pt-3 pb-1 flex flex-col gap-2 border-t border-[rgba(255,255,255,0.06)] mt-2">
                <Link href="/login" onClick={() => setOpen(false)}>
                  <button className="w-full py-2.5 text-sm text-[rgba(255,255,255,0.55)] border border-[rgba(255,255,255,0.08)] rounded-xl hover:text-white hover:bg-[rgba(255,255,255,0.04)] transition-all font-medium">
                    Log in
                  </button>
                </Link>
                <Link href="/register" onClick={() => setOpen(false)}>
                  <button className="w-full py-2.5 text-sm rounded-xl font-semibold bg-[#00E5A8] text-black">
                    Get API Key
                  </button>
                </Link>
              </div>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
