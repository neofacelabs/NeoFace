"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  // Shared
  Settings, LogOut, ChevronRight,
  // Admin icons
  LayoutDashboard, Users, Activity, BarChart3, ShieldAlert,
  Building2, Globe, Database, Key, Bell, FileText,
  // User icons
  Home, UserCircle, CreditCard, History, Shield, ShieldCheck,
  Fingerprint, Lock,
  // Biometrics tools (admin-only)
  Eye, Scan, Zap, Brain, Cpu, ShoppingBag,
  // Badges
  Crown, User,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { useRole } from "@/hooks/use-role";
import { authApi } from "@/lib/api";
import { firebaseLogout } from "@/lib/firebase-auth";
import { toast } from "sonner";

// ═══════════════════════════════════════════════════════════════════════════════
//  ADMIN Navigation — Full platform-wide visibility
// ═══════════════════════════════════════════════════════════════════════════════
const NAV_ADMIN_PLATFORM = [
  {
    href: "/dashboard",
    icon: LayoutDashboard,
    label: "Command Center",
    desc: "Global metrics & system health",
    badge: null,
  },
  {
    href: "/dashboard/users",
    icon: Users,
    label: "User Management",
    desc: "All enrolled identities",
    badge: null,
  },
  {
    href: "/dashboard/risk",
    icon: ShieldAlert,
    label: "Risk & Fraud",
    desc: "Platform-wide trust scores",
    badge: "new",
  },
  {
    href: "/dashboard/logs",
    icon: Activity,
    label: "Auth Logs",
    desc: "All authentication events",
    badge: null,
  },
  {
    href: "/dashboard/analytics",
    icon: BarChart3,
    label: "Analytics",
    desc: "Platform-wide insights",
    badge: null,
  },
  {
    href: "/dashboard/bank-accounts",
    icon: Building2,
    label: "Payment Methods",
    desc: "Linked bank accounts",
    badge: null,
  },
];

const NAV_ADMIN_SYSTEM = [
  {
    href: "/dashboard/settings",
    icon: Settings,
    label: "Platform Settings",
    desc: "API keys, thresholds, webhooks",
    badge: null,
  },
];

const NAV_ADMIN_TOOLS = [
  {
    href: "/dashboard/trust-engine",
    icon: Shield,
    label: "Trust Engine",
    desc: "8-module live biometric scan",
    badge: null,
  },
  {
    href: "/dashboard/identity",
    icon: UserCircle,
    label: "My Identity",
    desc: "Personal enrollment",
    badge: null,
  },
  {
    href: "/enroll",
    icon: Scan,
    label: "Onboard User",
    desc: "Enroll new biometrics",
    badge: null,
  },
  {
    href: "/verify",
    icon: ShieldCheck,
    label: "Pay Terminal",
    desc: "Biometric payment test",
    badge: null,
  },
  {
    href: "/checkout-demo",
    icon: ShoppingBag,
    label: "Checkout Demo",
    desc: "Live NeoFace Pay demo",
    badge: null,
  },
  {
    href: "/dashboard/active-liveness",
    icon: Eye,
    label: "Active Liveness",
    desc: "Challenge-response test",
    badge: null,
  },
  {
    href: "/dashboard/behavioral",
    icon: Zap,
    label: "Behavioral",
    desc: "Mouse/keyboard profiling",
    badge: null,
  },
  {
    href: "/dashboard/continuous-auth",
    icon: Activity,
    label: "Continuous Auth",
    desc: "Persistent session guard",
    badge: null,
  },
  {
    href: "/dashboard/fingerprint",
    icon: Fingerprint,
    label: "Fingerprint (WebAuthn)",
    desc: "FIDO2 passkey auth",
    badge: null,
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
//  USER Navigation — Personal data only
// ═══════════════════════════════════════════════════════════════════════════════
const NAV_USER_MAIN = [
  {
    href: "/dashboard",
    icon: Home,
    label: "My Overview",
    desc: "Personal activity & trust score",
    badge: null,
  },
  {
    href: "/dashboard/trust-engine",
    icon: Shield,
    label: "Trust Engine",
    desc: "Verify your identity live",
    badge: null,
  },
  {
    href: "/dashboard/identity",
    icon: UserCircle,
    label: "My Identity",
    desc: "Face enrollment & biometrics",
    badge: null,
  },
  {
    href: "/dashboard/bank-accounts",
    icon: CreditCard,
    label: "Payment Methods",
    desc: "My linked accounts",
    badge: null,
  },
  {
    href: "/dashboard/logs",
    icon: History,
    label: "My Transactions",
    desc: "Personal auth & payment log",
    badge: null,
  },
];

const NAV_USER_SECURITY = [
  {
    href: "/dashboard/fingerprint",
    icon: Fingerprint,
    label: "Fingerprint Auth",
    desc: "WebAuthn / FIDO2 passkey",
    badge: null,
  },
  {
    href: "/dashboard/behavioral",
    icon: Brain,
    label: "Behavior Profile",
    desc: "My mouse/keyboard pattern",
    badge: null,
  },
  {
    href: "/dashboard/continuous-auth",
    icon: Lock,
    label: "Session Guard",
    desc: "Continuous auth monitor",
    badge: null,
  },
  {
    href: "/dashboard/active-liveness",
    icon: Eye,
    label: "Liveness Test",
    desc: "Run a challenge test",
    badge: null,
  },
  {
    href: "/dashboard/settings",
    icon: Settings,
    label: "Security Settings",
    desc: "Account & auth preferences",
    badge: null,
  },
];

// ═══════════════════════════════════════════════════════════════════════════════
//  NavItem component
// ═══════════════════════════════════════════════════════════════════════════════
function NavItem({
  href, icon: Icon, label, desc, active, badge,
}: {
  href: string; icon: any; label: string; desc: string; active: boolean; badge?: string | null;
}) {
  return (
    <Link href={href} className="group block">
      <motion.div
        whileHover={{ x: 2 }}
        transition={{ duration: 0.15, ease: "easeOut" }}
        className={cn(
          "relative flex items-center gap-2.5 px-3 py-2 rounded-xl text-[12px] font-medium transition-all duration-200",
          active
            ? "bg-[rgba(0,194,255,0.08)] text-white border border-[rgba(0,194,255,0.2)]"
            : "text-[rgba(255,255,255,0.32)] hover:text-[rgba(255,255,255,0.7)] hover:bg-[rgba(255,255,255,0.04)] border border-transparent"
        )}
      >
        {/* Active glow */}
        {active && (
          <motion.div
            layoutId="nav-glow"
            className="absolute inset-0 rounded-xl pointer-events-none"
            style={{ boxShadow: "inset 0 0 20px rgba(0,194,255,0.06)" }}
          />
        )}

        <div className={cn(
          "w-6 h-6 rounded-lg flex items-center justify-center shrink-0 transition-all duration-200",
          active
            ? "bg-[rgba(0,194,255,0.15)] shadow-[0_0_8px_rgba(0,194,255,0.3)]"
            : "bg-[rgba(255,255,255,0.04)] group-hover:bg-[rgba(255,255,255,0.07)]"
        )}>
          <Icon size={12} className={active ? "text-[#00C2FF]" : "text-current"} />
        </div>

        <div className="min-w-0 flex-1">
          <p className="leading-tight truncate">{label}</p>
          {active && (
            <p className="text-[9.5px] text-[rgba(0,194,255,0.5)] leading-tight mt-0.5 truncate">{desc}</p>
          )}
        </div>

        {/* Badge (e.g. "new") */}
        {badge && (
          <span className="shrink-0 px-1.5 py-0.5 rounded-full text-[8px] font-bold uppercase tracking-wider"
            style={{ background: "rgba(0,229,168,0.15)", color: "#00E5A8", border: "1px solid rgba(0,229,168,0.3)" }}>
            {badge}
          </span>
        )}

        {active && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="w-1.5 h-1.5 rounded-full bg-[#00C2FF] shrink-0 shadow-[0_0_4px_#00C2FF]"
          />
        )}
      </motion.div>
    </Link>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  NavSection label
// ═══════════════════════════════════════════════════════════════════════════════
function NavSection({ label }: { label: string }) {
  return (
    <p className="text-[9px] text-[rgba(255,255,255,0.2)] uppercase tracking-widest px-3 pb-1.5 pt-3.5 font-semibold">
      {label}
    </p>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
//  DashboardLayout
// ═══════════════════════════════════════════════════════════════════════════════
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, logout } = useAuthStore();
  const { isAdmin } = useRole();
  const router = useRouter();
  const pathname = usePathname();
  const [time, setTime] = useState("");

  const [hydrated, setHydrated] = useState(false);

  // Wait for Zustand persist middleware to rehydrate from localStorage.
  // Without this, isAuthenticated is `false` on the very first render
  // even for a logged-in user, causing an immediate redirect to /login.
  useEffect(() => {
    // useAuthStore.persist.hasHydrated() is true once rehydration is done.
    if ((useAuthStore as any).persist?.hasHydrated()) {
      setHydrated(true);
    } else {
      const unsub = (useAuthStore as any).persist?.onFinishHydration(() => {
        setHydrated(true);
      });
      return () => unsub?.();
    }
  }, []);

  useEffect(() => {
    if (hydrated && !isAuthenticated) router.push("/login");
  }, [hydrated, isAuthenticated, router]);

  // Live clock
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const handleLogout = async () => {
    try { await authApi.logout(); } catch {}
    try { await firebaseLogout(); } catch {}
    logout();
    toast.success("Signed out");
    router.push("/");
  };

  const isActive = (href: string) =>
    pathname === href || (href !== "/dashboard" && pathname.startsWith(href) && href.startsWith("/dashboard"));

  return (
    <div
      className="min-h-screen flex"
      style={{ background: "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(0,194,255,0.04) 0%, transparent 60%), #030303" }}
    >
      {/* Background grid */}
      <div
        className="fixed inset-0 pointer-events-none z-0 opacity-[0.025]"
        style={{
          backgroundImage: "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* ── Sidebar ──────────────────────────────────────────────────────────── */}
      <motion.aside
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className="w-[228px] shrink-0 flex flex-col fixed inset-y-0 left-0 z-30"
        style={{
          background: "rgba(3,3,3,0.9)",
          backdropFilter: "blur(24px)",
          borderRight: "1px solid rgba(0,194,255,0.08)",
          boxShadow: "4px 0 40px rgba(0,0,0,0.5), 1px 0 0 rgba(0,194,255,0.05)",
        }}
      >
        {/* ── Logo ─────────────────────────────────────────────────────────── */}
        <div className="px-4 h-[60px] flex items-center" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
          <Link href="/" className="flex items-center gap-2.5 group">
            <Image src="/logo.png" alt="NeoFace Logo" width={200} height={60} className="h-10 w-auto object-contain" priority loading="eager" />
            <div>
              <p className="text-[9px] text-[rgba(255,255,255,0.25)] tracking-widest uppercase leading-none mt-0.5">
                {isAdmin ? "Admin Panel" : "Payment Infra"}
              </p>
            </div>
          </Link>
        </div>

        {/* ── Environment + Role badge ──────────────────────────────────────── */}
        <div className="px-4 py-3 space-y-2">
          {/* Live indicator */}
          <div
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg"
            style={{ background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.12)" }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ background: "#00E5A8", boxShadow: "0 0 6px #00E5A8", animation: "pulse 2s infinite" }}
            />
            <span className="text-[10px] text-[rgba(0,229,168,0.8)] font-medium flex-1">Live Environment</span>
            <span className="text-[9px] text-[rgba(255,255,255,0.2)] font-mono">{time}</span>
          </div>

          {/* Role badge */}
          <div
            className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg"
            style={{
              background: isAdmin ? "rgba(99,102,241,0.08)" : "rgba(0,194,255,0.05)",
              border: isAdmin ? "1px solid rgba(99,102,241,0.2)" : "1px solid rgba(0,194,255,0.12)",
            }}
          >
            {isAdmin
              ? <Crown size={10} style={{ color: "#818cf8" }} />
              : <User size={10} style={{ color: "#00C2FF" }} />
            }
            <span className="text-[10px] font-semibold flex-1"
              style={{ color: isAdmin ? "#818cf8" : "#00C2FF" }}>
              {isAdmin ? "Administrator" : "Standard User"}
            </span>
            <ChevronRight size={9} style={{ color: "rgba(255,255,255,0.15)" }} />
          </div>
        </div>

        {/* ── Navigation (role-specific) ────────────────────────────────────── */}
        <nav className="flex-1 px-3 overflow-y-auto pb-2">
          {isAdmin ? (
            // ─── ADMIN NAV ───────────────────────────────────────────────────
            <>
              <NavSection label="Platform" />
              {NAV_ADMIN_PLATFORM.map(item => (
                <NavItem key={item.href} {...item} active={isActive(item.href)} />
              ))}

              <NavSection label="System" />
              {NAV_ADMIN_SYSTEM.map(item => (
                <NavItem key={item.href} {...item} active={isActive(item.href)} />
              ))}

              <NavSection label="Developer Playground" />
              {NAV_ADMIN_TOOLS.map(item => (
                <NavItem key={item.href} {...item} active={isActive(item.href)} />
              ))}
            </>
          ) : (
            // ─── USER NAV ────────────────────────────────────────────────────
            <>
              <NavSection label="My Account" />
              {NAV_USER_MAIN.map(item => (
                <NavItem key={item.href} {...item} active={isActive(item.href)} />
              ))}

              <NavSection label="Security & Biometrics" />
              {NAV_USER_SECURITY.map(item => (
                <NavItem key={item.href} {...item} active={isActive(item.href)} />
              ))}
            </>
          )}
        </nav>

        {/* ── Bottom — Settings + Logout + Avatar ──────────────────────────── */}
        <div className="p-3 space-y-0.5" style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-[12px] font-medium text-[rgba(255,255,255,0.3)] hover:text-[#f87171] hover:bg-[rgba(248,113,113,0.06)] transition-all"
          >
            <LogOut size={13} />
            Sign out
          </button>

          {/* Avatar row */}
          <div className="mt-2 px-3 py-2 flex items-center gap-2.5">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0"
              style={{
                background: isAdmin ? "rgba(99,102,241,0.2)" : "rgba(0,194,255,0.15)",
                border: isAdmin ? "1px solid rgba(99,102,241,0.35)" : "1px solid rgba(0,194,255,0.25)",
                color: isAdmin ? "#818cf8" : "#00C2FF",
                boxShadow: isAdmin ? "0 0 8px rgba(99,102,241,0.2)" : "0 0 8px rgba(0,194,255,0.2)",
              }}
            >
              {user?.name?.[0]?.toUpperCase() ?? "U"}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[12px] font-medium text-[rgba(255,255,255,0.6)] truncate">{user?.name ?? "User"}</div>
              <div className="text-[9.5px] font-semibold uppercase tracking-wider truncate"
                style={{ color: isAdmin ? "rgba(99,102,241,0.6)" : "rgba(0,194,255,0.4)" }}>
                {isAdmin ? "Admin" : "User"} · {user?.email?.split("@")[0] ?? "—"}
              </div>
            </div>
          </div>
        </div>
      </motion.aside>

      {/* ── Main content ──────────────────────────────────────────────────────── */}
      <main className="flex-1 ml-[228px] min-h-screen relative z-10">
        <div className="p-8 page-in max-w-[1440px]">
          {children}
        </div>
      </main>
    </div>
  );
}
