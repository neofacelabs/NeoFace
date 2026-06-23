"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Mail, Lock, User, Eye, EyeOff, ArrowRight, Check } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { authApi } from "@/lib/api";
import { cn, extractErrorMsg } from "@/lib/utils";

const schema = z.object({
  name:     z.string().min(2, "Name must be at least 2 characters"),
  email:    z.string().email("Enter a valid email"),
  password: z.string()
    .min(8, "Minimum 8 characters")
    .regex(/[A-Z]/, "Include one uppercase letter")
    .regex(/[0-9]/, "Include one number"),
  confirm:  z.string(),
}).refine((d) => d.password === d.confirm, {
  message: "Passwords do not match",
  path: ["confirm"],
});
type Form = z.infer<typeof schema>;

const RULES = [
  { label: "8+ characters", test: (p: string) => p.length >= 8 },
  { label: "Uppercase",     test: (p: string) => /[A-Z]/.test(p) },
  { label: "Number",        test: (p: string) => /[0-9]/.test(p) },
];



export default function RegisterPage() {
  const [showPass, setShowPass] = useState(false);
  const router = useRouter();

  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm<Form>({
    resolver: zodResolver(schema),
  });

  const password = watch("password", "");

  const onSubmit = async (data: Form) => {
    try {
      await authApi.register({ name: data.name, email: data.email, password: data.password });
      toast.success("Account created — sign in to continue");
      router.push("/login");
    } catch (err: any) {
      toast.error(extractErrorMsg(err, "Registration failed"));
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4 py-12 relative overflow-hidden">
      <div className="absolute inset-0 hero-glow opacity-60 pointer-events-none" />
      <div className="absolute inset-0 dot-grid opacity-[0.3] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative w-full max-w-[400px]"
      >
        <Link href="/" className="flex items-center justify-center gap-2.5 mb-10">
          <Image src="/NeoFaceLogoFinal.png" alt="NeoFace Logo" width={200} height={60} className="h-12 w-auto object-contain" />
        </Link>

        <div className="rounded-2xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-8">
          <h1 className="text-lg font-semibold text-white mb-1 tracking-tight">Create account</h1>
          <p className="text-sm text-[rgba(255,255,255,0.38)] mb-7">
            Face enrollment follows after sign-up.
          </p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input
              label="Full name"
              placeholder="Alex Johnson"
              icon={<User size={15} />}
              error={errors.name?.message}
              autoComplete="name"
              {...register("name")}
            />
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
                autoComplete="new-password"
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

            {/* Strength indicators */}
            {password.length > 0 && (
              <div className="flex gap-4 pt-0.5">
                {RULES.map((r) => (
                  <div
                    key={r.label}
                    className={cn(
                      "flex items-center gap-1 text-[11px] transition-colors",
                      r.test(password) ? "text-[#34d399]" : "text-[rgba(255,255,255,0.25)]"
                    )}
                  >
                    <Check size={10} />
                    {r.label}
                  </div>
                ))}
              </div>
            )}

            <Input
              label="Confirm password"
              type="password"
              placeholder="••••••••"
              icon={<Lock size={15} />}
              error={errors.confirm?.message}
              autoComplete="new-password"
              {...register("confirm")}
            />

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full btn-accent py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 group mt-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              ) : (
                <>
                  Create account
                  <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-[rgba(255,255,255,0.06)] text-center">
            <p className="text-xs text-[rgba(255,255,255,0.35)]">
              Already have an account?{" "}
              <Link href="/login" className="text-[#a5b4fc] hover:text-white transition-colors font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
