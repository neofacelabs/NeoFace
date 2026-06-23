"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, AppWindow, Key, Users, Database, Fingerprint,
  ShieldCheck, Activity, BarChart3, Webhook, BookOpen, Settings,
  LogOut, ChevronDown, Building2, Globe, ShieldAlert, Cpu, Server,
  CreditCard, Scan, Zap, Eye, Brain, Lock, AlertTriangle,
  CheckCircle2, ArrowUpRight, Menu, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/auth";
import { useRole } from "@/hooks/use-role";
import { authApi } from "@/lib/api";
import { firebaseLogout } from "@/lib/firebase-auth";
import { toast } from "sonner";

/* ═══════════════════════════════════════════════════════════════════════════
   CUSTOMER NAV
   ═══════════════════════════════════════════════════════════════════════════ */
const CUSTOMER_NAV = [
  {
    section: "Overview",
    items: [
      { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard", exact: true },
    ],
  },
  {
    section: "Build",
    items: [
      { href: "/dashboard/applications", icon: AppWindow,  label: "Applications" },
      { href: "/dashboard/api-keys",     icon: Key,         label: "API Keys" },
      { href: "/dashboard/users",        icon: Users,       label: "Users" },
      { href: "/dashboard/identity",     icon: Database,    label: "Identity Store" },
    ],
  },
  {
    section: "Observe",
    items: [
      { href: "/dashboard/sessions",     icon: Activity,    label: "Auth Sessions" },
      { href: "/dashboard/analytics",    icon: BarChart3,   label: "Analytics" },
      { href: "/dashboard/logs",         icon: Eye,         label: "Audit Logs" },
    ],
  },
  {
    section: "Connect",
    items: [
      { href: "/dashboard/webhooks",     icon: Webhook,     label: "Webhooks" },
      { href: "/dashboard/trust-engine", icon: ShieldCheck, label: "Trust Engine" },
      { href: "/dashboard/fingerprint",  icon: Fingerprint, label: "Passkeys (WebAuthn)" },
    ],
  },
  {
    section: "Account",
    items: [
      { href: "/dashboard/settings",     icon: Settings,    label: "Settings" },
    ],
  },
];

/* ═══════════════════════════════════════════════════════════════════════════
   ADMIN NAV
   ═══════════════════════════════════════════════════════════════════════════ */
const ADMIN_NAV = [
  {
    section: "Overview",
    items: [
      { href: "/dashboard",              icon: LayoutDashboard, label: "Command Center", exact: true },
    ],
  },
  {
    section: "Platform",
    items: [
      { href: "/dashboard/users",        icon: Building2,   label: "Organizations" },
      { href: "/dashboard/applications", icon: AppWindow,   label: "Applications" },
      { href: "/dashboard/identity",     icon: Database,    label: "Identity Storage" },
    ],
  },
  {
    section: "Monitoring",
    items: [
      { href: "/dashboard/analytics",    icon: BarChart3,   label: "API Monitoring" },
      { href: "/dashboard/risk",         icon: ShieldAlert, label: "Fraud Center" },
      { href: "/dashboard/models",       icon: Brain,       label: "Model Monitoring" },
    ],
  },
  {
    section: "Operations",
    items: [
      { href: "/dashboard/infrastructure", icon: Server,   label: "Infrastructure" },
      { href: "/dashboard/logs",           icon: Activity,  label: "Audit Logs" },
      { href: "/dashboard/bank-accounts",  icon: CreditCard, label: "Billing" },
    ],
  },
  {
    section: "Admin",
    items: [
      { href: "/dashboard/trust-engine", icon: ShieldCheck, label: "Trust Engine" },
      { href: "/dashboard/active-liveness", icon: Scan,    label: "Liveness Lab" },
      { href: "/dashboard/behavioral",   icon: Zap,        label: "Behavioral" },
      { href: "/dashboard/continuous-auth", icon: Lock,    label: "Continuous Auth" },
      { href: "/dashboard/settings",     icon: Settings,    label: "Settings" },
    ],
  },
];

/* ═══════════════════════════════════════════════════════════════════════════
   NAV ITEM
   ═══════════════════════════════════════════════════════════════════════════ */
function NavItem({
  href, icon: Icon, label, active,
}: {
  href: string; icon: any; label: string; active: boolean;
}) {
  return (
    <Link href={href} className={cn("nav-item", active && "active")}>
      <span
        className="w-[18px] h-[18px] flex items-center justify-center shrink-0"
        style={{ color: active ? "#00C2FF" : "rgba(255,255,255,0.35)" }}
      >
        <Icon size={13} />
      </span>
      <span className="truncate">{label}</span>
      {active && (
        <span
          className="ml-auto w-1.5 h-1.5 rounded-full shrink-0"
          style={{ background: "#00C2FF", boxShadow: "0 0 5px #00C2FF" }}
        />
      )}
    </Link>
  );
}

function NavSection({ label }: { label: string }) {
  return (
    <p className="px-2.5 pt-5 pb-1 text-[9.5px] font-semibold tracking-[0.12em] uppercase text-[rgba(255,255,255,0.2)]">
      {label}
    </p>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   DASHBOARD LAYOUT
   ═══════════════════════════════════════════════════════════════════════════ */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user, logout } = useAuthStore();
  const { isAdmin } = useRole();
  const router = useRouter();
  const pathname = usePathname();
  const [time, setTime] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  /* ── Hydration guard ─────────────────────────────────────────────────── */
  useEffect(() => {
    if ((useAuthStore as any).persist?.hasHydrated()) {
      setHydrated(true);
    } else {
      const unsub = (useAuthStore as any).persist?.onFinishHydration(() => setHydrated(true));
      return () => unsub?.();
    }
  }, []);

  useEffect(() => {
    if (hydrated && !isAuthenticated) router.push("/login");
  }, [hydrated, isAuthenticated, router]);

  /* ── Live clock ──────────────────────────────────────────────────────── */
  useEffect(() => {
    const tick = () =>
      setTime(new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false }));
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

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : (pathname === href || pathname.startsWith(href + "/"));

  const nav = isAdmin ? ADMIN_NAV : CUSTOMER_NAV;

  const Sidebar = (
    <aside
      className="flex flex-col h-full"
      style={{
        background: "rgba(5,5,5,0.96)",
        borderRight: "1px solid rgba(255,255,255,0.055)",
      }}
    >
      {/* ── Logo ── */}
      <div
        className="flex items-center gap-2.5 px-4 h-[56px] shrink-0"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
      >
        <Link href="/" className="flex items-center gap-2 group">
          <Image
            src="/NeoFaceLogoFinal.png" alt="NeoFace" width={120} height={36}
            className="h-7 w-auto object-contain"
            priority
          />
        </Link>
        <div
          className="ml-auto text-[9px] font-semibold px-1.5 py-0.5 rounded-full tracking-wide"
          style={{
            background: isAdmin ? "rgba(129,140,248,0.12)" : "rgba(0,194,255,0.1)",
            color: isAdmin ? "#818cf8" : "#00C2FF",
            border: isAdmin ? "1px solid rgba(129,140,248,0.2)" : "1px solid rgba(0,194,255,0.2)",
          }}
        >
          {isAdmin ? "ADMIN" : "LABS"}
        </div>
      </div>

      {/* ── Status bar ── */}
      <div className="px-3 py-2.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
        <div
          className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg"
          style={{ background: "rgba(0,229,168,0.04)", border: "1px solid rgba(0,229,168,0.09)" }}
        >
          <span className="status-dot-live shrink-0" />
          <span className="text-[10.5px] text-[rgba(0,229,168,0.75)] font-medium flex-1">
            {isAdmin ? "Operations Live" : "Production"}
          </span>
          <span className="text-[9px] text-[rgba(255,255,255,0.2)] font-mono">{time}</span>
        </div>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto px-2.5 pb-3 space-y-0.5">
        {nav.map((group) => (
          <div key={group.section}>
            <NavSection label={group.section} />
            {group.items.map((item) => (
              <NavItem
                key={item.href}
                href={item.href}
                icon={item.icon}
                label={item.label}
                active={isActive(item.href, (item as any).exact)}
              />
            ))}
          </div>
        ))}
      </nav>

      {/* ── User footer ── */}
      <div
        className="px-3 py-3 shrink-0 space-y-1"
        style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}
      >
        <button
          onClick={handleLogout}
          className="nav-item w-full"
          style={{ color: "rgba(255,255,255,0.3)" }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "#f87171"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.3)"; }}
        >
          <LogOut size={13} />
          Sign out
        </button>

        <div className="flex items-center gap-2.5 px-2 py-2.5 rounded-lg mt-1"
          style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.05)" }}>
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0"
            style={{
              background: isAdmin ? "rgba(129,140,248,0.15)" : "rgba(0,194,255,0.12)",
              color: isAdmin ? "#818cf8" : "#00C2FF",
              border: isAdmin ? "1px solid rgba(129,140,248,0.25)" : "1px solid rgba(0,194,255,0.2)",
            }}
          >
            {user?.name?.[0]?.toUpperCase() ?? "U"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[12px] font-medium text-[rgba(255,255,255,0.75)] truncate leading-tight">
              {user?.name ?? "User"}
            </p>
            <p className="text-[9.5px] text-[rgba(255,255,255,0.3)] truncate leading-tight mt-0.5">
              {user?.email ?? "—"}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );

  return (
    <div
      className="min-h-screen flex"
      style={{ background: "#050505" }}
    >
      {/* ── Subtle dot grid ── */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        style={{
          backgroundImage: "radial-gradient(rgba(255,255,255,0.025) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
          maskImage: "linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)",
          WebkitMaskImage: "linear-gradient(to bottom, transparent, black 10%, black 90%, transparent)",
        }}
      />

      {/* ── Desktop Sidebar ── */}
      <div
        className="hidden lg:flex flex-col w-[220px] shrink-0 fixed inset-y-0 left-0 z-30"
        style={{ backdropFilter: "blur(20px)" }}
      >
        {Sidebar}
      </div>

      {/* ── Mobile sidebar backdrop ── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/70 lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.div
              initial={{ x: -220 }} animate={{ x: 0 }} exit={{ x: -220 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed inset-y-0 left-0 w-[220px] z-50 lg:hidden"
            >
              {Sidebar}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Main content ── */}
      <main className="flex-1 lg:ml-[220px] min-h-screen relative z-10 flex flex-col">
        {/* Mobile header */}
        <div
          className="flex lg:hidden items-center gap-3 px-4 h-14 shrink-0"
          style={{ borderBottom: "1px solid rgba(255,255,255,0.05)", background: "rgba(5,5,5,0.95)" }}
        >
          <button onClick={() => setMobileOpen(true)}>
            <Menu size={18} className="text-[rgba(255,255,255,0.5)]" />
          </button>
          <Image src="/NeoFaceLogoFinal.png" alt="NeoFace" width={100} height={30} className="h-6 w-auto" />
        </div>

        <div className="flex-1 p-6 lg:p-8 page-in">
          {children}
        </div>
      </main>
    </div>
  );
}
