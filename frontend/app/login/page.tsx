"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Mail, Lock, Eye, EyeOff, ArrowRight, Zap, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/store/auth";
import { signInWithGoogle } from "@/lib/firebase-auth";
import type { User } from "@/types";

// ── Demo accounts ─────────────────────────────────────────────────────────────
const DEMO_ACCOUNTS = [
  {
    role: "Admin",
    email: "admin@neoface.io",
    password: "AdminPass123!",
    color: "#a5b4fc",
    dot: "bg-[#a5b4fc]",
  },
  {
    role: "Viewer",
    email: "demo@neoface.io",
    password: "DemoPass123!",
    color: "#34d399",
    dot: "bg-[#34d399]",
  },
] as const;

function mockUserForEmail(email: string): User {
  const isAdmin = email === "admin@neoface.io";
  return {
    id: isAdmin ? "00000000-0000-0000-0000-000000000001" : "00000000-0000-0000-0000-000000000002",
    name: isAdmin ? "NeoFace Admin" : "Demo User",
    email,
    role: isAdmin ? "admin" : "user",
    is_active: true,
    is_enrolled: isAdmin,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
}

const MOCK_CREDENTIALS: Record<string, string> = {
  "admin@neoface.io": "AdminPass123!",
  "demo@neoface.io":  "DemoPass123!",
};

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password required"),
});
type Form = z.infer<typeof schema>;

// ── Google icon ───────────────────────────────────────────────────────────────
function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}



export default function LoginPage() {
  const [showPass, setShowPass] = useState(false);
  const [backendDown, setBackendDown] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const router = useRouter();
  const { setTokens, setUser } = useAuthStore();

  const {
    register, handleSubmit, setValue,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) });

  const fillDemo = (email: string, password: string) => {
    setValue("email", email, { shouldValidate: true });
    setValue("password", password, { shouldValidate: true });
    setBackendDown(false);
  };

  // ── Google Sign-In ───────────────────────────────────────────────────────────
  const handleGoogleSignIn = async () => {
    setGoogleLoading(true);
    try {
      const fbUser = await signInWithGoogle();
      const idToken = await fbUser.getIdToken();

      // Try to exchange Firebase token for a real NeoFace JWT from the backend
      try {
        const { data: tokens } = await authApi.googleSignIn(idToken);
        setTokens(tokens.access_token, tokens.refresh_token);
        // Fetch the real user profile from the backend DB
        const { data: user } = await authApi.me();
        setUser(user);
        toast.success(`Welcome, ${user.name}! 🎉`, { description: "Signed in with Google" });
      } catch (backendErr: any) {
        // Backend is offline or Firebase creds not configured — fall back to Firebase-only mode
        const neoUser: User = {
          id: fbUser.uid,
          name: fbUser.displayName ?? fbUser.email?.split("@")[0] ?? "User",
          email: fbUser.email ?? "",
          role: "user",
          is_active: true,
          is_enrolled: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        setTokens(`firebase-${fbUser.uid}`, `firebase-refresh-${fbUser.uid}`);
        setUser(neoUser);
        toast.success(`Welcome, ${neoUser.name}! 🎉`, {
          description: "Signed in with Google (demo mode)",
        });
      }

      router.push("/dashboard");
    } catch (err: any) {
      // User cancelled popup — don't show error
      if (err?.code !== "auth/popup-closed-by-user" && err?.code !== "auth/cancelled-popup-request") {
        toast.error("Google sign-in failed — try again");
      }
    } finally {
      setGoogleLoading(false);
    }
  };

  // ── Email/password submit ────────────────────────────────────────────────────
  const onSubmit = async (data: Form) => {
    try {
      const { data: tokens } = await authApi.login(data.email, data.password);
      setTokens(tokens.access_token, tokens.refresh_token);
      const { data: user } = await authApi.me();
      setUser(user);
      toast.success(`Welcome back, ${user.name}`);
      router.push("/dashboard");
      return;
    } catch (err: any) {
      const isNetworkError =
        !err?.response ||
        err?.code === "ERR_NETWORK" ||
        err?.code === "ECONNREFUSED";

      if (isNetworkError) {
        const expectedPassword = MOCK_CREDENTIALS[data.email];
        if (expectedPassword && data.password === expectedPassword) {
          const mockUser = mockUserForEmail(data.email);
          setTokens("demo-token-" + data.email, "demo-refresh-" + data.email);
          setUser(mockUser);
          toast.success(`Demo mode — Welcome, ${mockUser.name}`, {
            description: "Backend offline. Running with mock data.",
          });
          setBackendDown(false);
          router.push("/dashboard");
          return;
        }
        setBackendDown(true);
        toast.error("Wrong password for demo account");
        return;
      }

      const status = err?.response?.status;
      if (status === 401 || status === 403) {
        toast.error("Invalid email or password");
      } else {
        toast.error("Something went wrong — try again");
      }
      setBackendDown(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4 relative overflow-hidden">
      <div className="absolute inset-0 hero-glow opacity-60 pointer-events-none" />
      <div className="absolute inset-0 dot-grid opacity-[0.3] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-[380px]"
      >
        {/* Logo */}
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-8">
          <Image src="/logo.png" alt="NeoFace Logo" width={200} height={60} className="h-12 w-auto object-contain" />
        </Link>

        {/* Backend offline banner */}
        {backendDown && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 rounded-xl border border-[rgba(251,191,36,0.25)] bg-[rgba(251,191,36,0.06)] p-3.5 flex items-start gap-3"
          >
            <AlertCircle size={14} className="text-[#fbbf24] shrink-0 mt-0.5" />
            <div>
              <p className="text-[12px] font-medium text-[#fbbf24]">Backend offline</p>
              <p className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5 leading-relaxed">
                Use a demo account below to explore the dashboard with mock data.
              </p>
            </div>
          </motion.div>
        )}

        {/* Demo credentials */}
        <div className="mb-4 rounded-xl border border-[rgba(124,124,255,0.2)] bg-[rgba(124,124,255,0.05)] p-4">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={12} className="text-[#a5b4fc]" />
            <span className="text-[11px] font-semibold text-[#a5b4fc] uppercase tracking-wider">
              Demo access
            </span>
          </div>
          <div className="space-y-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.role}
                type="button"
                onClick={() => fillDemo(acc.email, acc.password)}
                className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.06)] hover:bg-[rgba(255,255,255,0.07)] hover:border-[rgba(255,255,255,0.10)] transition-all duration-150 group text-left"
              >
                <div className="flex items-center gap-2.5">
                  <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${acc.dot}`} />
                  <div>
                    <p className="text-[12px] font-medium text-white leading-tight">{acc.role}</p>
                    <p className="text-[10px] text-[rgba(255,255,255,0.3)] font-mono">{acc.email}</p>
                  </div>
                </div>
                <span
                  className="text-[11px] font-medium opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  style={{ color: acc.color }}
                >
                  Fill ↵
                </span>
              </button>
            ))}
          </div>
          <p className="text-[10px] text-[rgba(255,255,255,0.22)] mt-3 leading-relaxed">
            Works even when the backend is offline — runs in demo mode automatically.
          </p>
        </div>

        {/* Login card */}
        <div className="rounded-2xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-8">
          <h1 className="text-lg font-semibold text-white mb-1 tracking-tight">Welcome back</h1>
          <p className="text-sm text-[rgba(255,255,255,0.38)] mb-7">
            Sign in to your NeoFace account
          </p>

          {/* ── Google Sign-In Button ── */}
          <motion.button
            type="button"
            onClick={handleGoogleSignIn}
            disabled={googleLoading}
            whileHover={{ scale: 1.01, borderColor: "rgba(255,255,255,0.2)" }}
            whileTap={{ scale: 0.99 }}
            className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl border border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.04)] text-white text-[13.5px] font-medium mb-5 transition-all disabled:opacity-60 disabled:cursor-not-allowed hover:bg-[rgba(255,255,255,0.07)]"
          >
            {googleLoading ? (
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <GoogleIcon />
            )}
            {googleLoading ? "Signing in…" : "Continue with Google"}
          </motion.button>

          {/* OR divider */}
          <div className="relative flex items-center gap-3 mb-5">
            <div className="flex-1 h-px bg-[rgba(255,255,255,0.07)]" />
            <span className="text-[11px] text-[rgba(255,255,255,0.22)] shrink-0">or sign in with email</span>
            <div className="flex-1 h-px bg-[rgba(255,255,255,0.07)]" />
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@company.com"
              icon={<Mail size={15} />}
              error={errors.email?.message}
              autoComplete="email"
              {...register("email")}
            />
            <div className="relative">
              <Input
                label="Password"
                type={showPass ? "text" : "password"}
                placeholder="••••••••"
                icon={<Lock size={15} />}
                error={errors.password?.message}
                autoComplete="current-password"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                className="absolute right-3.5 top-8 text-[rgba(255,255,255,0.3)] hover:text-[rgba(255,255,255,0.6)] transition-colors"
              >
                {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>

            <div className="flex justify-end">
              <Link
                href="/forgot-password"
                className="text-xs text-[rgba(124,124,255,0.7)] hover:text-[#a5b4fc] transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full btn-accent py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 group mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <>
                  Sign in
                  <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-[rgba(255,255,255,0.06)] text-center">
            <p className="text-xs text-[rgba(255,255,255,0.35)]">
              No account?{" "}
              <Link href="/register" className="text-[#a5b4fc] hover:text-white transition-colors font-medium">
                Create one free
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
