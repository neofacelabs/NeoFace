"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { User, Shield, Key, Save } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/auth";
import { toast } from "sonner";

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await new Promise(r => setTimeout(r, 900));
    toast.success("Settings saved");
    setSaving(false);
  };

  const cardClass = "rounded-2xl border border-[rgba(255,255,255,0.07)] bg-[rgba(255,255,255,0.025)] overflow-hidden";

  return (
    <div className="space-y-5 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-[13px] text-[rgba(255,255,255,0.35)] mt-0.5">Manage your account and security preferences</p>
      </div>

      {[
        {
          icon: User, title: "Profile",
          fields: [
            { label: "Full Name", value: user?.name ?? "", placeholder: "Your name" },
            { label: "Email",     value: user?.email ?? "", placeholder: "your@email.com", type: "email" },
          ],
        },
        {
          icon: Shield, title: "Security",
          fields: [
            { label: "Current Password", value: "", placeholder: "••••••••", type: "password" },
            { label: "New Password",     value: "", placeholder: "••••••••", type: "password" },
          ],
        },
      ].map((section, i) => {
        const Icon = section.icon;
        return (
          <motion.div
            key={section.title}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={cardClass}
          >
            <div className="px-5 py-4 border-b border-[rgba(255,255,255,0.06)] flex items-center gap-3">
              <div className="w-7 h-7 rounded-lg bg-[rgba(124,124,255,0.1)] flex items-center justify-center">
                <Icon size={13} className="text-[#a5b4fc]" />
              </div>
              <h2 className="text-sm font-semibold text-white">{section.title}</h2>
            </div>
            <div className="p-5 space-y-4">
              {section.fields.map((f) => (
                <Input
                  key={f.label}
                  label={f.label}
                  defaultValue={f.value}
                  placeholder={f.placeholder}
                  type={(f as any).type ?? "text"}
                />
              ))}
            </div>
          </motion.div>
        );
      })}

      {/* Account info */}
      <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className={cardClass}>
        <div className="px-5 py-4 border-b border-[rgba(255,255,255,0.06)] flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-[rgba(124,124,255,0.1)] flex items-center justify-center">
            <Key size={13} className="text-[#a5b4fc]" />
          </div>
          <h2 className="text-sm font-semibold text-white">Account</h2>
        </div>
        <div className="p-5 space-y-3">
          {[
            { label: "Account ID", value: (user?.id?.slice(0, 8) ?? "—") + "…" },
            { label: "Role",       value: user?.role ?? "user" },
            { label: "Enrolled",   value: user?.is_enrolled ? "Yes" : "No" },
          ].map(({ label, value }) => (
            <div key={label} className="flex items-center justify-between py-2.5 border-b border-[rgba(255,255,255,0.05)] last:border-0">
              <span className="text-[13px] text-[rgba(255,255,255,0.38)]">{label}</span>
              <span className="text-[13px] text-white font-medium font-mono">{value}</span>
            </div>
          ))}
        </div>
      </motion.div>

      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-accent px-5 py-2.5 rounded-xl text-sm font-semibold text-white flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? (
            <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
          ) : <Save size={13} />}
          Save Changes
        </button>
      </div>
    </div>
  );
}
