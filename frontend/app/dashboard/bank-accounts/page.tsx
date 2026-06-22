"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Building2, CreditCard, Plus, Trash2, Star, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { bankAccountsApi } from "@/lib/api";
import { toast } from "sonner";
import type { BankAccount } from "@/types";

/* ── Add Account Modal ────────────────────────────────────────────────────── */
function AddAccountModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ bank_name: "", account_number_last4: "", account_type: "checking", routing_number: "" });
  const mutation = useMutation({
    mutationFn: () => bankAccountsApi.link({ ...form, token: `mock_${Date.now()}` }),
    onSuccess: () => {
      toast.success("Bank account linked successfully");
      qc.invalidateQueries({ queryKey: ["bank-accounts"] });
      onClose();
    },
    onError: () => toast.error("Failed to link bank account"),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(8px)" }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-md rounded-2xl p-6"
        style={{ background: "rgba(12,12,12,0.98)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 24px 80px rgba(0,0,0,0.7)" }}
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.2)" }}>
            <Building2 size={16} style={{ color: "#00C2FF" }} />
          </div>
          <div>
            <h2 className="text-[15px] font-semibold text-white">Link Bank Account</h2>
            <p className="text-[11px] text-[rgba(255,255,255,0.3)]">Connect your payment account to NeoFace</p>
          </div>
        </div>

        <div className="space-y-3">
          {[
            { key: "bank_name", label: "Bank Name", placeholder: "e.g. Chase, Bank of America" },
            { key: "account_number_last4", label: "Last 4 Digits", placeholder: "XXXX" },
            { key: "routing_number", label: "Routing Number", placeholder: "9-digit routing number" },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-[11px] text-[rgba(255,255,255,0.4)] mb-1.5 font-medium uppercase tracking-wider">{f.label}</label>
              <input
                value={(form as any)[f.key]}
                onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))}
                placeholder={f.placeholder}
                className="w-full px-3.5 py-2.5 rounded-xl text-[13px] text-white placeholder-[rgba(255,255,255,0.2)] outline-none transition-all"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
                onFocus={e => (e.currentTarget.style.borderColor = "rgba(0,194,255,0.4)")}
                onBlur={e => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)")}
              />
            </div>
          ))}

          <div>
            <label className="block text-[11px] text-[rgba(255,255,255,0.4)] mb-1.5 font-medium uppercase tracking-wider">Account Type</label>
            <select
              value={form.account_type}
              onChange={e => setForm(p => ({ ...p, account_type: e.target.value }))}
              className="w-full px-3.5 py-2.5 rounded-xl text-[13px] text-white outline-none"
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}
            >
              <option value="checking">Checking</option>
              <option value="savings">Savings</option>
            </select>
          </div>
        </div>

        <div className="flex gap-2 mt-5">
          <button onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl text-[12.5px] font-medium transition-all"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.5)" }}>
            Cancel
          </button>
          <button onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !form.bank_name || !form.account_number_last4}
            className="flex-1 px-4 py-2.5 rounded-xl text-[12.5px] font-semibold transition-all flex items-center justify-center gap-2"
            style={{ background: "rgba(0,194,255,0.15)", border: "1px solid rgba(0,194,255,0.3)", color: "#00C2FF" }}>
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Link Account
          </button>
        </div>
      </motion.div>
    </div>
  );
}

/* ── Account Card ─────────────────────────────────────────────────────────── */
function AccountCard({ account, index }: { account: BankAccount; index: number }) {
  const qc = useQueryClient();
  const setDefault = useMutation({
    mutationFn: () => bankAccountsApi.setDefault(account.id),
    onSuccess: () => { toast.success("Default payment account updated"); qc.invalidateQueries({ queryKey: ["bank-accounts"] }); },
  });
  const unlink = useMutation({
    mutationFn: () => bankAccountsApi.unlink(account.id),
    onSuccess: () => { toast.success("Bank account removed"); qc.invalidateQueries({ queryKey: ["bank-accounts"] }); },
    onError: () => toast.error("Failed to remove account"),
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      whileHover={{ y: -1, transition: { duration: 0.2 } }}
      className="relative group rounded-2xl p-5"
      style={{
        background: account.is_default ? "rgba(0,194,255,0.04)" : "rgba(255,255,255,0.02)",
        border: account.is_default ? "1px solid rgba(0,194,255,0.2)" : "1px solid rgba(255,255,255,0.07)",
        boxShadow: "0 1px 20px rgba(0,0,0,0.35)",
      }}
    >
      {account.is_default && (
        <div className="absolute top-0 left-8 right-8 h-px"
          style={{ background: "linear-gradient(90deg, transparent, rgba(0,194,255,0.5), transparent)" }} />
      )}

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: account.is_default ? "rgba(0,194,255,0.12)" : "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <Building2 size={18} style={{ color: account.is_default ? "#00C2FF" : "rgba(255,255,255,0.4)" }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-[14px] font-semibold text-white">{account.bank_name}</p>
              {account.is_default && (
                <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-semibold"
                  style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}>
                  <Star size={8} fill="currentColor" />
                  DEFAULT
                </span>
              )}
            </div>
            <p className="text-[12px] text-[rgba(255,255,255,0.35)] mt-0.5 capitalize">
              {account.account_type} •••• {account.last_four}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {account.is_verified && (
            <div className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium"
              style={{ background: "rgba(0,229,168,0.08)", color: "#00E5A8" }}>
              <CheckCircle size={10} />
              Verified
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-4 pt-4"
        style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }}>
        {!account.is_default && (
          <button onClick={() => setDefault.mutate()}
            disabled={setDefault.isPending}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-[11.5px] font-medium transition-all"
            style={{ background: "rgba(0,194,255,0.06)", border: "1px solid rgba(0,194,255,0.15)", color: "rgba(0,194,255,0.7)" }}>
            {setDefault.isPending ? <Loader2 size={11} className="animate-spin" /> : <Star size={11} />}
            Set Default
          </button>
        )}
        <button onClick={() => unlink.mutate()}
          disabled={unlink.isPending}
          className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-[11.5px] font-medium transition-all"
          style={{ background: "rgba(248,113,113,0.05)", border: "1px solid rgba(248,113,113,0.15)", color: "rgba(248,113,113,0.6)" }}>
          {unlink.isPending ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
          Remove
        </button>
      </div>
    </motion.div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────────────── */
export default function BankAccountsPage() {
  const [showModal, setShowModal] = useState(false);
  const { data, isLoading } = useQuery<{ accounts: BankAccount[] }>({
    queryKey: ["bank-accounts"],
    queryFn: () => bankAccountsApi.list().then(r => r.data),
  });
  const accounts = data?.accounts ?? [];

  return (
    <>
      <AnimatePresence>{showModal && <AddAccountModal onClose={() => setShowModal(false)} />}</AnimatePresence>

      <div className="space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-start justify-between"
        >
          <div>

            <h1 className="text-[22px] font-bold text-white tracking-tight">Bank Accounts</h1>
            <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">
              Linked payment accounts for biometric transactions
            </p>
          </div>
          <button onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-[12.5px] font-semibold transition-all"
            style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,194,255,0.15)")}
            onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,194,255,0.1)")}>
            <Plus size={14} />
            Link Account
          </button>
        </motion.div>

        {/* Content */}
        {isLoading ? (
          <div className="grid md:grid-cols-2 gap-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-32 rounded-2xl animate-pulse" style={{ background: "rgba(255,255,255,0.04)" }} />
            ))}
          </div>
        ) : accounts.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-16 rounded-2xl"
            style={{ background: "rgba(255,255,255,0.015)", border: "1px dashed rgba(255,255,255,0.08)" }}>
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
              style={{ background: "rgba(0,194,255,0.08)", border: "1px solid rgba(0,194,255,0.15)" }}>
              <Building2 size={24} style={{ color: "rgba(0,194,255,0.5)" }} />
            </div>
            <p className="text-[14px] font-semibold text-white mb-1">No bank accounts linked</p>
            <p className="text-[12px] text-[rgba(255,255,255,0.3)] mb-5 text-center max-w-xs">
              Link a bank account to enable biometric payment authorization
            </p>
            <button onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-[12.5px] font-semibold"
              style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.25)", color: "#00C2FF" }}>
              <Plus size={14} />
              Link First Account
            </button>
          </motion.div>
        ) : (
          <div className="grid md:grid-cols-2 gap-3">
            {accounts.map((acc, i) => <AccountCard key={acc.id} account={acc} index={i} />)}
          </div>
        )}

        {/* Info note */}
        {accounts.length > 0 && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}
            className="flex items-start gap-3 p-4 rounded-xl"
            style={{ background: "rgba(0,194,255,0.04)", border: "1px solid rgba(0,194,255,0.1)" }}>
            <AlertCircle size={14} style={{ color: "rgba(0,194,255,0.5)", marginTop: 1 }} className="shrink-0" />
            <p className="text-[11.5px] text-[rgba(255,255,255,0.3)] leading-relaxed">
              Payment authorizations will debit your <span style={{ color: "#00C2FF" }}>default account</span> using biometric identity verification.
              Account numbers are never stored in full — only a secure tokenized reference is kept.
            </p>
          </motion.div>
        )}
      </div>
    </>
  );
}
