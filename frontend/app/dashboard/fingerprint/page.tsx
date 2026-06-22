"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Fingerprint, Shield, ShieldCheck, ShieldAlert, Smartphone,
  Trash2, Pencil, Check, X, Clock, Wifi, WifiOff, CreditCard,
  AlertTriangle, ChevronRight, Lock, Unlock, RefreshCw,
  Monitor, Tablet, Eye, Zap, Activity, Settings, RotateCcw,
  CheckCircle2, XCircle, Info, Bell, Key, Mail, Phone,
} from "lucide-react";
import { toast } from "sonner";
import { webAuthnApi } from "@/lib/api";

/* ── Types ────────────────────────────────────────────────────────────────── */
interface Device {
  id: string;
  device_name: string;
  aaguid: string | null;
  is_active: boolean;
  fingerprint_payments_enabled: boolean;
  enrolled_at: string;
  last_used_at: string | null;
}

type Tab = "enroll" | "devices" | "security" | "pay";
type EnrollStep = "check" | "unsupported" | "ready" | "scanning" | "success" | "error";

/* ── Helpers ──────────────────────────────────────────────────────────────── */
function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

function base64urlToBuffer(base64url: string): ArrayBuffer {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
  const binary = atob(padded);
  const buffer = new ArrayBuffer(binary.length);
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return buffer;
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

/* ── Fingerprint Pulse Animation ─────────────────────────────────────────── */
function FingerprintPulse({ state }: { state: "idle" | "scanning" | "success" | "error" }) {
  const colors: Record<string, string> = {
    idle: "#818cf8",
    scanning: "#00E5A8",
    success: "#34d399",
    error: "#f87171",
  };
  const color = colors[state];

  return (
    <div className="relative flex items-center justify-center w-36 h-36">
      {/* Outer rings */}
      {(state === "scanning" || state === "idle") && [1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border"
          style={{ borderColor: color + "40", width: 36 + i * 28, height: 36 + i * 28 }}
          animate={{ scale: [1, 1.15, 1], opacity: [0.6, 0.1, 0.6] }}
          transition={{ duration: 2, delay: i * 0.3, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}

      {/* Glow ring */}
      <motion.div
        className="absolute rounded-full"
        style={{ width: 80, height: 80, background: `radial-gradient(circle, ${color}30 0%, transparent 70%)` }}
        animate={state === "scanning" ? { scale: [1, 1.3, 1], opacity: [0.8, 0.3, 0.8] } : {}}
        transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* Icon */}
      <motion.div
        className="relative z-10 w-16 h-16 rounded-2xl flex items-center justify-center"
        style={{ background: `linear-gradient(135deg, ${color}25 0%, ${color}10 100%)`, border: `1px solid ${color}50` }}
        animate={state === "scanning" ? { boxShadow: [`0 0 0px ${color}80`, `0 0 30px ${color}80`, `0 0 0px ${color}80`] } : {}}
        transition={{ duration: 1.2, repeat: Infinity }}
      >
        {state === "success" ? (
          <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300 }}>
            <CheckCircle2 size={32} style={{ color }} />
          </motion.div>
        ) : state === "error" ? (
          <XCircle size={32} style={{ color }} />
        ) : (
          <Fingerprint size={32} style={{ color }} />
        )}
      </motion.div>

      {/* Scan line */}
      {state === "scanning" && (
        <motion.div
          className="absolute rounded-full overflow-hidden"
          style={{ width: 64, height: 64, clipPath: "circle(32px)" }}
        >
          <motion.div
            className="absolute w-full h-0.5"
            style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }}
            animate={{ y: [-32, 32, -32] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
        </motion.div>
      )}
    </div>
  );
}

/* ── Enroll Flow ──────────────────────────────────────────────────────────── */
function EnrollFlow({ onSuccess }: { onSuccess: () => void }) {
  const [step, setStep] = useState<EnrollStep>("check");
  const [deviceName, setDeviceName] = useState("My Device");
  const [error, setError] = useState("");
  const [supported, setSupported] = useState(false);
  const [editingName, setEditingName] = useState(false);

  useEffect(() => {
    async function check() {
      try {
        const ok = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        setSupported(ok);
        // Auto-detect device name
        const ua = navigator.userAgent.toLowerCase();
        if (ua.includes("iphone") || ua.includes("ipad")) setDeviceName("iPhone / iPad (Touch ID)");
        else if (ua.includes("mac")) setDeviceName("Mac (Touch ID / Face ID)");
        else if (ua.includes("windows")) setDeviceName("Windows PC (Windows Hello)");
        else if (ua.includes("android")) setDeviceName("Android Device");
        setStep(ok ? "ready" : "unsupported");
      } catch {
        setStep("unsupported");
      }
    }
    check();
  }, []);

  const handleEnroll = useCallback(async () => {
    setStep("scanning");
    setError("");
    try {
      // 1 — Get challenge from server
      const beginRes = await webAuthnApi.registerBegin();
      const options = beginRes.data;

      // 2 — Convert challenge/user.id to ArrayBuffer
      const publicKey: PublicKeyCredentialCreationOptions = {
        ...options,
        challenge: base64urlToBuffer(options.challenge),
        user: {
          ...options.user,
          id: base64urlToBuffer(options.user.id),
        },
        excludeCredentials: (options.excludeCredentials || []).map((c: any) => ({
          ...c,
          id: base64urlToBuffer(c.id),
        })),
      };

      // 3 — Browser triggers native fingerprint prompt
      const credential = await navigator.credentials.create({ publicKey }) as PublicKeyCredential;
      if (!credential) throw new Error("No credential returned");

      const attestation = credential.response as AuthenticatorAttestationResponse;

      // 4 — Send only public key artifacts to server (never private key)
      await webAuthnApi.registerComplete({
        credential_id: bufferToBase64url(credential.rawId),
        raw_id: bufferToBase64url(credential.rawId),
        response: {
          clientDataJSON: bufferToBase64url(attestation.clientDataJSON),
          attestationObject: bufferToBase64url(attestation.attestationObject),
        },
        type: credential.type,
        device_name: deviceName,
        device_metadata: {
          platform: navigator.platform,
        },
      });

      setStep("success");
      setTimeout(() => onSuccess(), 1800);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Enrollment failed";
      if (msg.includes("cancelled") || msg.includes("NotAllowedError")) {
        setError("Fingerprint prompt was cancelled. Please try again.");
      } else {
        setError(msg);
      }
      setStep("error");
    }
  }, [deviceName, onSuccess]);

  return (
    <div className="flex flex-col items-center gap-8 py-6">
      {/* State machine UI */}
      {step === "check" && (
        <div className="flex flex-col items-center gap-4">
          <FingerprintPulse state="scanning" />
          <p className="text-sm text-white/50">Checking device capabilities…</p>
        </div>
      )}

      {step === "unsupported" && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center gap-5 max-w-sm text-center">
          <div className="w-16 h-16 rounded-2xl bg-[#f87171]/10 border border-[#f87171]/30 flex items-center justify-center">
            <WifiOff size={28} className="text-[#f87171]" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-1">No Fingerprint Sensor Found</h3>
            <p className="text-sm text-white/50 leading-relaxed">
              Your device or browser does not support hardware biometric authentication (WebAuthn Platform Authenticator).
            </p>
          </div>
          <div className="w-full rounded-xl bg-white/4 border border-white/8 p-4 text-left space-y-2">
            <p className="text-xs font-medium text-white/70 mb-2">Supported devices:</p>
            {[
              { icon: Smartphone, label: "iPhone / iPad with Touch ID or Face ID" },
              { icon: Monitor, label: "Mac with Touch ID" },
              { icon: Monitor, label: "Windows PC with Windows Hello" },
              { icon: Smartphone, label: "Android with fingerprint sensor" },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2.5 text-xs text-white/50">
                <Icon size={13} className="text-white/30 shrink-0" />
                {label}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {step === "ready" && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center gap-6 w-full max-w-sm">
          <FingerprintPulse state="idle" />

          {/* Device name */}
          <div className="w-full">
            <label className="text-xs text-white/50 mb-1.5 block">Device name</label>
            {editingName ? (
              <div className="flex gap-2">
                <input
                  autoFocus
                  value={deviceName}
                  onChange={e => setDeviceName(e.target.value)}
                  className="flex-1 bg-white/5 border border-white/15 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-[#818cf8]/60"
                  maxLength={60}
                />
                <button onClick={() => setEditingName(false)} className="px-3 rounded-lg bg-[#818cf8]/20 text-[#818cf8] text-sm hover:bg-[#818cf8]/30 transition-colors">
                  <Check size={14} />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setEditingName(true)}
                className="w-full flex items-center justify-between bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white hover:border-white/20 transition-colors"
              >
                <span>{deviceName}</span>
                <Pencil size={12} className="text-white/30" />
              </button>
            )}
          </div>

          <div className="w-full rounded-xl bg-[#00E5A8]/6 border border-[#00E5A8]/20 p-4 space-y-2">
            {[
              "Your private key stays inside this device's secure enclave",
              "NeoFace stores only your public key — no fingerprint images",
              "You can revoke this device at any time",
            ].map(t => (
              <div key={t} className="flex items-start gap-2 text-xs text-[#00E5A8]/80">
                <ShieldCheck size={12} className="mt-0.5 shrink-0" />
                {t}
              </div>
            ))}
          </div>

          <button
            id="fingerprint-enroll-btn"
            onClick={handleEnroll}
            className="w-full py-3.5 rounded-xl font-semibold text-sm text-black transition-all active:scale-95"
            style={{ background: "linear-gradient(135deg, #00E5A8 0%, #818cf8 100%)" }}
          >
            Enroll Fingerprint
          </button>
        </motion.div>
      )}

      {step === "scanning" && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-5">
          <FingerprintPulse state="scanning" />
          <div className="text-center">
            <p className="text-base font-medium text-white">Touch the fingerprint sensor</p>
            <p className="text-sm text-white/40 mt-1">Follow your device's prompt to authenticate</p>
          </div>
          <div className="flex gap-1.5">
            {[0, 1, 2].map(i => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-[#00E5A8]"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.2, delay: i * 0.2, repeat: Infinity }}
              />
            ))}
          </div>
        </motion.div>
      )}

      {step === "success" && (
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center gap-4">
          <FingerprintPulse state="success" />
          <div className="text-center">
            <p className="text-lg font-semibold text-white">Device Enrolled!</p>
            <p className="text-sm text-white/50 mt-1">Your fingerprint is now registered securely</p>
          </div>
        </motion.div>
      )}

      {step === "error" && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col items-center gap-5 max-w-sm text-center">
          <FingerprintPulse state="error" />
          <div>
            <p className="text-base font-semibold text-white">Enrollment Failed</p>
            <p className="text-sm text-[#f87171] mt-1">{error}</p>
          </div>
          <button
            onClick={() => { setStep("ready"); setError(""); }}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-white/6 border border-white/10 text-sm text-white hover:bg-white/10 transition-colors"
          >
            <RotateCcw size={14} /> Try Again
          </button>
        </motion.div>
      )}
    </div>
  );
}

/* ── Device Card ──────────────────────────────────────────────────────────── */
function DeviceCard({ device, onRevoke, onRename, onTogglePayments }: {
  device: Device;
  onRevoke: (id: string) => void;
  onRename: (id: string, name: string) => void;
  onTogglePayments: (id: string, enabled: boolean) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(device.device_name);
  const [confirmRevoke, setConfirmRevoke] = useState(false);

  const ua = device.device_name.toLowerCase();
  const DeviceIcon = ua.includes("iphone") || ua.includes("android") || ua.includes("ipad") ? Smartphone
    : ua.includes("mac") || ua.includes("windows") ? Monitor : Tablet;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className="relative rounded-xl border p-4 transition-all"
      style={{
        background: device.is_active ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.02)",
        borderColor: device.is_active ? "rgba(255,255,255,0.10)" : "rgba(255,255,255,0.05)",
      }}
    >
      {/* Status dot */}
      <div className="absolute top-3.5 right-3.5 flex items-center gap-1.5">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: device.is_active ? "#34d399" : "#6b7280" }}
        />
        <span className="text-[10px]" style={{ color: device.is_active ? "#34d399" : "#6b7280" }}>
          {device.is_active ? "Active" : "Revoked"}
        </span>
      </div>

      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
          style={{
            background: device.is_active ? "rgba(129,140,248,0.15)" : "rgba(255,255,255,0.05)",
            border: `1px solid ${device.is_active ? "rgba(129,140,248,0.3)" : "rgba(255,255,255,0.08)"}`,
          }}
        >
          <DeviceIcon size={18} style={{ color: device.is_active ? "#818cf8" : "#6b7280" }} />
        </div>

        <div className="flex-1 min-w-0 pr-12">
          {editing ? (
            <div className="flex gap-2 mb-2">
              <input
                autoFocus
                value={name}
                onChange={e => setName(e.target.value)}
                className="flex-1 bg-white/5 border border-white/15 rounded-lg px-2 py-1 text-sm text-white outline-none focus:border-[#818cf8]/60"
              />
              <button
                onClick={() => { onRename(device.id, name); setEditing(false); }}
                className="px-2 rounded-lg bg-[#818cf8]/20 text-[#818cf8]"
              >
                <Check size={13} />
              </button>
              <button
                onClick={() => { setName(device.device_name); setEditing(false); }}
                className="px-2 rounded-lg bg-white/5 text-white/40"
              >
                <X size={13} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 mb-1">
              <p className="text-sm font-medium text-white truncate">{device.device_name}</p>
              {device.is_active && (
                <button onClick={() => setEditing(true)} className="text-white/25 hover:text-white/60 transition-colors">
                  <Pencil size={11} />
                </button>
              )}
            </div>
          )}

          <div className="flex flex-wrap gap-x-3 gap-y-1">
            <span className="flex items-center gap-1 text-[11px] text-white/40">
              <Clock size={9} />
              Enrolled {relativeTime(device.enrolled_at)}
            </span>
            {device.last_used_at && (
              <span className="flex items-center gap-1 text-[11px] text-white/40">
                <Activity size={9} />
                Last used {relativeTime(device.last_used_at)}
              </span>
            )}
          </div>

          {/* Payment toggle */}
          {device.is_active && (
            <div className="flex items-center gap-2 mt-3">
              <button
                onClick={() => onTogglePayments(device.id, !device.fingerprint_payments_enabled)}
                className="relative w-8 h-4.5 rounded-full transition-colors shrink-0"
                style={{
                  background: device.fingerprint_payments_enabled ? "#00E5A8" : "rgba(255,255,255,0.12)",
                  height: "18px",
                }}
              >
                <motion.div
                  className="absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white shadow"
                  animate={{ x: device.fingerprint_payments_enabled ? 14 : 2 }}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              </button>
              <span className="text-[11px] text-white/50">
                Fingerprint payments {device.fingerprint_payments_enabled ? "enabled" : "disabled"}
              </span>
              <CreditCard size={10} className="text-white/30" />
            </div>
          )}
        </div>
      </div>

      {/* Revoke */}
      {device.is_active && (
        <div className="mt-3 pt-3 border-t border-white/6">
          {confirmRevoke ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-[#f87171] flex-1">Revoke this device?</span>
              <button
                onClick={() => { onRevoke(device.id); setConfirmRevoke(false); }}
                className="px-3 py-1 rounded-lg bg-[#f87171]/15 text-[#f87171] text-xs hover:bg-[#f87171]/25 transition-colors"
              >
                Yes, revoke
              </button>
              <button
                onClick={() => setConfirmRevoke(false)}
                className="px-3 py-1 rounded-lg bg-white/5 text-white/40 text-xs"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmRevoke(true)}
              className="flex items-center gap-1.5 text-[11px] text-white/30 hover:text-[#f87171] transition-colors"
            >
              <Trash2 size={11} />
              Revoke access
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}

/* ── Payment Demo ─────────────────────────────────────────────────────────── */
type PayState = "idle" | "form" | "challenge" | "mfa_face" | "mfa_otp" | "processing" | "approved" | "rejected";

function PaymentDemo({ hasDevices }: { hasDevices: boolean }) {
  const [state, setState] = useState<PayState>("idle");
  const [amount, setAmount] = useState("");
  const [merchant, setMerchant] = useState("Zara — Fashion Store");
  const [challengeData, setChallengeData] = useState<any>(null);
  const [otp, setOtp] = useState("");
  const [result, setResult] = useState<any>(null);

  const riskTier = () => {
    const n = parseFloat(amount) || 0;
    if (n < 1000) return { tier: "low", label: "Low Risk", color: "#34d399", factors: ["Fingerprint"] };
    if (n <= 10000) return { tier: "medium", label: "Medium Risk", color: "#fbbf24", factors: ["Fingerprint", "Face Auth"] };
    return { tier: "high", label: "High Risk", color: "#f87171", factors: ["Fingerprint", "Face Auth", "OTP"] };
  };

  const handlePayBegin = async () => {
    if (!amount || isNaN(parseFloat(amount))) {
      toast.error("Enter a valid amount");
      return;
    }
    try {
      setState("challenge");
      const res = await webAuthnApi.paymentBegin({
        amount: parseFloat(amount),
        currency: "INR",
        merchant_name: merchant,
      });
      setChallengeData(res.data);

      // Convert challenge to ArrayBuffer
      const publicKey: PublicKeyCredentialRequestOptions = {
        challenge: base64urlToBuffer(res.data.challenge),
        rpId: res.data.rpId,
        allowCredentials: (res.data.allowCredentials || []).map((c: any) => ({
          ...c,
          id: base64urlToBuffer(c.id),
        })),
        userVerification: "required",
      };

      const assertion = await navigator.credentials.get({ publicKey }) as PublicKeyCredential;
      if (!assertion) throw new Error("Authentication cancelled");

      const assertionResponse = assertion.response as AuthenticatorAssertionResponse;

      // For medium/high tier, request face auth next
      if (res.data.risk_tier === "medium" || res.data.risk_tier === "high") {
        setState("mfa_face");
        // Simulate face auth completion
        await new Promise(r => setTimeout(r, 2000));
        if (res.data.risk_tier === "high") {
          setState("mfa_otp");
          return; // Wait for OTP input
        }
      }

      setState("processing");
      const completeRes = await webAuthnApi.paymentComplete({
        transaction_ref: res.data.transaction_ref,
        credential_id: bufferToBase64url(assertion.rawId),
        raw_id: bufferToBase64url(assertion.rawId),
        response: {
          clientDataJSON: bufferToBase64url(assertionResponse.clientDataJSON),
          authenticatorData: bufferToBase64url(assertionResponse.authenticatorData),
          signature: bufferToBase64url(assertionResponse.signature),
          userHandle: assertionResponse.userHandle ? bufferToBase64url(assertionResponse.userHandle) : undefined,
        } as any,
        type: assertion.type,
      });

      setResult(completeRes.data);
      setState("approved");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Payment failed";
      if (msg.includes("cancel") || msg.includes("NotAllowed")) {
        toast.error("Fingerprint verification cancelled");
        setState("form");
      } else {
        setResult({ error: msg });
        setState("rejected");
      }
    }
  };

  const handleOtpConfirm = () => {
    if (otp.length < 4) { toast.error("Enter the OTP"); return; }
    setState("processing");
    setTimeout(() => { setResult({ authorized: true, amount, currency: "INR", merchant_name: merchant }); setState("approved"); }, 1500);
  };

  const risk = riskTier();

  return (
    <div className="space-y-5">
      <AnimatePresence mode="wait">
        {state === "idle" && (
          <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-5 py-8">
            <div className="w-16 h-16 rounded-2xl bg-[#818cf8]/10 border border-[#818cf8]/25 flex items-center justify-center">
              <CreditCard size={28} className="text-[#818cf8]" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-semibold text-white">Fingerprint Payment Demo</h3>
              <p className="text-sm text-white/45 mt-1">Simulate a WebAuthn-signed payment transaction</p>
            </div>
            {!hasDevices ? (
              <div className="flex items-center gap-2 text-sm text-[#fbbf24]/80 bg-[#fbbf24]/8 border border-[#fbbf24]/20 rounded-xl px-4 py-3">
                <AlertTriangle size={14} className="shrink-0" />
                Enroll a fingerprint device first
              </div>
            ) : (
              <button
                id="pay-demo-start"
                onClick={() => setState("form")}
                className="px-6 py-3 rounded-xl font-semibold text-sm text-black"
                style={{ background: "linear-gradient(135deg, #818cf8 0%, #00E5A8 100%)" }}
              >
                Start Payment Demo
              </button>
            )}
          </motion.div>
        )}

        {state === "form" && (
          <motion.div key="form" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-4 max-w-sm mx-auto">
            <h3 className="text-sm font-semibold text-white">New Payment</h3>

            <div>
              <label className="text-xs text-white/50 mb-1.5 block">Amount (₹)</label>
              <input
                type="number"
                placeholder="e.g. 4999"
                value={amount}
                onChange={e => setAmount(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm outline-none focus:border-[#818cf8]/50"
              />
            </div>

            <div>
              <label className="text-xs text-white/50 mb-1.5 block">Merchant</label>
              <input
                value={merchant}
                onChange={e => setMerchant(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-sm outline-none focus:border-[#818cf8]/50"
              />
            </div>

            {/* Risk indicator */}
            {amount && (
              <motion.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-xl p-3.5 space-y-2"
                style={{ background: `${risk.color}10`, border: `1px solid ${risk.color}30` }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium" style={{ color: risk.color }}>{risk.label}</span>
                  <Shield size={12} style={{ color: risk.color }} />
                </div>
                <div className="flex gap-2 flex-wrap">
                  {risk.factors.map(f => (
                    <span key={f} className="text-[11px] px-2 py-0.5 rounded-full" style={{ background: `${risk.color}20`, color: risk.color }}>
                      {f}
                    </span>
                  ))}
                </div>
              </motion.div>
            )}

            <div className="flex gap-2 pt-1">
              <button
                onClick={() => setState("idle")}
                className="flex-1 py-3 rounded-xl text-sm text-white/50 border border-white/8 hover:bg-white/5"
              >
                Cancel
              </button>
              <button
                id="pay-confirm-btn"
                onClick={handlePayBegin}
                className="flex-2 flex-1 py-3 rounded-xl text-sm font-semibold text-black"
                style={{ background: "linear-gradient(135deg, #00E5A8 0%, #818cf8 100%)" }}
              >
                Confirm with Fingerprint
              </button>
            </div>
          </motion.div>
        )}

        {state === "challenge" && (
          <motion.div key="challenge" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-5 py-8">
            <FingerprintPulse state="scanning" />
            <p className="text-sm text-white font-medium">Touch fingerprint sensor to authorize ₹{amount}</p>
            <p className="text-xs text-white/40">{merchant}</p>
          </motion.div>
        )}

        {state === "mfa_face" && (
          <motion.div key="mfa_face" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-5 py-8">
            <div className="w-16 h-16 rounded-2xl bg-[#00E5A8]/10 border border-[#00E5A8]/25 flex items-center justify-center">
              <motion.div animate={{ scale: [1, 1.1, 1] }} transition={{ duration: 1.5, repeat: Infinity }}>
                <Eye size={28} className="text-[#00E5A8]" />
              </motion.div>
            </div>
            <p className="text-sm text-white font-medium">Face authentication required</p>
            <p className="text-xs text-white/40">High-value transaction · Looking at camera…</p>
          </motion.div>
        )}

        {state === "mfa_otp" && (
          <motion.div key="mfa_otp" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4 max-w-sm mx-auto py-4">
            <div className="flex flex-col items-center gap-3 mb-4">
              <div className="w-14 h-14 rounded-2xl bg-[#fbbf24]/10 border border-[#fbbf24]/25 flex items-center justify-center">
                <Mail size={24} className="text-[#fbbf24]" />
              </div>
              <p className="text-sm font-medium text-white">OTP Verification</p>
              <p className="text-xs text-white/45 text-center">We sent a 6-digit code to your registered email/phone for this high-value payment.</p>
            </div>
            <input
              type="text"
              maxLength={6}
              placeholder="Enter 6-digit OTP"
              value={otp}
              onChange={e => setOtp(e.target.value.replace(/\D/g, ""))}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white text-center text-lg tracking-widest outline-none focus:border-[#fbbf24]/50"
            />
            <button
              onClick={handleOtpConfirm}
              className="w-full py-3 rounded-xl text-sm font-semibold text-black"
              style={{ background: "linear-gradient(135deg, #fbbf24 0%, #f87171 100%)" }}
            >
              Verify & Authorize
            </button>
          </motion.div>
        )}

        {state === "processing" && (
          <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col items-center gap-4 py-10">
            <motion.div
              className="w-12 h-12 rounded-full border-2 border-[#818cf8] border-t-transparent"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            />
            <p className="text-sm text-white/60">Verifying signature…</p>
          </motion.div>
        )}

        {state === "approved" && (
          <motion.div key="approved" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center gap-5 py-6">
            <motion.div
              className="w-20 h-20 rounded-full flex items-center justify-center"
              style={{ background: "radial-gradient(circle, #34d39930, transparent)" }}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <CheckCircle2 size={44} className="text-[#34d399]" />
            </motion.div>
            <div className="text-center">
              <p className="text-xl font-bold text-white">Payment Approved</p>
              <p className="text-2xl font-bold mt-1" style={{ color: "#00E5A8" }}>₹{result?.amount || amount}</p>
              <p className="text-sm text-white/50 mt-1">{result?.merchant_name || merchant}</p>
            </div>
            {result?.risk_tier && (
              <div className="text-xs text-white/40">Verified via {result.required_factors?.join(" + ") || "Fingerprint"}</div>
            )}
            <button
              onClick={() => { setState("idle"); setAmount(""); setResult(null); }}
              className="px-5 py-2.5 rounded-xl text-sm text-white/60 border border-white/10 hover:bg-white/5"
            >
              New Payment
            </button>
          </motion.div>
        )}

        {state === "rejected" && (
          <motion.div key="rejected" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center gap-4 py-6">
            <XCircle size={48} className="text-[#f87171]" />
            <div className="text-center">
              <p className="text-base font-semibold text-white">Payment Rejected</p>
              <p className="text-sm text-[#f87171] mt-1">{result?.error || "Signature verification failed"}</p>
            </div>
            <button onClick={() => { setState("idle"); setResult(null); }} className="px-5 py-2.5 rounded-xl text-sm text-white/60 border border-white/10 hover:bg-white/5">
              Try Again
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ── Security Center ──────────────────────────────────────────────────────── */
function SecurityCenter({ devices }: { devices: Device[] }) {
  const activeCount = devices.filter(d => d.is_active).length;

  return (
    <div className="space-y-4">
      {/* Security score */}
      <div
        className="rounded-xl p-5"
        style={{ background: "linear-gradient(135deg, rgba(0,229,168,0.08) 0%, rgba(129,140,248,0.08) 100%)", border: "1px solid rgba(0,229,168,0.2)" }}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-white">Security Level</span>
          <span className="text-xs text-[#00E5A8]">{activeCount > 0 ? "Protected" : "Unprotected"}</span>
        </div>
        <div className="h-2 rounded-full bg-white/8 overflow-hidden">
          <motion.div
            className="h-full rounded-full"
            style={{ background: "linear-gradient(90deg, #00E5A8, #818cf8)" }}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, activeCount * 40 + 20)}%` }}
            transition={{ duration: 1, ease: "easeOut" }}
          />
        </div>
        <p className="text-xs text-white/40 mt-2">{activeCount} active device{activeCount !== 1 ? "s" : ""} enrolled</p>
      </div>

      {/* Risk tiers */}
      <div className="rounded-xl border border-white/8 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/6">
          <p className="text-sm font-medium text-white">Payment Security Rules</p>
        </div>
        {[
          { range: "Below ₹1,000", factors: "Fingerprint only", color: "#34d399", icon: Lock },
          { range: "₹1,000 – ₹10,000", factors: "Fingerprint + Face Auth", color: "#fbbf24", icon: Shield },
          { range: "Above ₹10,000", factors: "Fingerprint + Face + OTP", color: "#f87171", icon: ShieldAlert },
        ].map(({ range, factors, color, icon: Icon }) => (
          <div key={range} className="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
              <Icon size={14} style={{ color }} />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-white">{range}</p>
              <p className="text-[11px] text-white/45">{factors}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Options */}
      <div className="rounded-xl border border-white/8 overflow-hidden">
        <div className="px-4 py-3 border-b border-white/6">
          <p className="text-sm font-medium text-white">Security Options</p>
        </div>
        {[
          { icon: Bell, label: "Payment Alerts", desc: "Email/SMS on every biometric payment", defaultOn: true },
          { icon: Activity, label: "Login History", desc: "Track all fingerprint authentication events", defaultOn: true },
          { icon: Key, label: "Recovery Methods", desc: "Face auth + Email + SMS OTP fallbacks", defaultOn: true },
          { icon: Phone, label: "Trusted Devices Only", desc: "Block payments from unknown devices", defaultOn: false },
        ].map(({ icon: Icon, label, desc, defaultOn }) => {
          const [on, setOn] = useState(defaultOn);
          return (
            <div key={label} className="flex items-center gap-3 px-4 py-3.5 border-b border-white/5 last:border-0">
              <Icon size={15} className="text-white/40 shrink-0" />
              <div className="flex-1">
                <p className="text-xs font-medium text-white">{label}</p>
                <p className="text-[11px] text-white/40">{desc}</p>
              </div>
              <button
                onClick={() => setOn(!on)}
                className="relative rounded-full transition-colors shrink-0"
                style={{ width: 32, height: 18, background: on ? "#00E5A8" : "rgba(255,255,255,0.12)" }}
              >
                <motion.div
                  className="absolute top-[2px] w-3.5 h-3.5 rounded-full bg-white shadow"
                  animate={{ x: on ? 14 : 2 }}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              </button>
            </div>
          );
        })}
      </div>

      {/* Recovery methods */}
      <div className="rounded-xl border border-white/8 p-4 space-y-3">
        <p className="text-sm font-medium text-white mb-1">Recovery Methods</p>
        <p className="text-xs text-white/40">If your fingerprint device is unavailable, you can recover access via:</p>
        {[
          { icon: Eye, label: "Face Authentication", status: "Available", color: "#00E5A8" },
          { icon: Mail, label: "Verified Email", status: "Available", color: "#818cf8" },
          { icon: Phone, label: "Mobile OTP", status: "Not set up", color: "#6b7280" },
        ].map(({ icon: Icon, label, status, color }) => (
          <div key={label} className="flex items-center gap-2.5">
            <Icon size={13} style={{ color }} className="shrink-0" />
            <span className="text-xs text-white/60 flex-1">{label}</span>
            <span className="text-[10px]" style={{ color }}>{status}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════════
   MAIN PAGE
══════════════════════════════════════════════════════════════════════════════ */
export default function FingerprintPage() {
  const [tab, setTab] = useState<Tab>("enroll");
  const qc = useQueryClient();

  const { data: devicesData, isLoading } = useQuery({
    queryKey: ["webauthn-devices"],
    queryFn: () => webAuthnApi.listDevices().then(r => r.data),
    refetchInterval: 15000,
  });

  const devices: Device[] = devicesData?.devices || [];
  const hasActiveDevices = devices.some(d => d.is_active);

  const revokeMutation = useMutation({
    mutationFn: (id: string) => webAuthnApi.revokeDevice(id),
    onSuccess: () => { toast.success("Device revoked"); qc.invalidateQueries({ queryKey: ["webauthn-devices"] }); },
    onError: () => toast.error("Failed to revoke device"),
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => webAuthnApi.renameDevice(id, name),
    onSuccess: () => { toast.success("Device renamed"); qc.invalidateQueries({ queryKey: ["webauthn-devices"] }); },
    onError: () => toast.error("Failed to rename device"),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => webAuthnApi.togglePayments(id, enabled),
    onSuccess: () => { toast.success("Payment setting updated"); qc.invalidateQueries({ queryKey: ["webauthn-devices"] }); },
    onError: () => toast.error("Failed to update setting"),
  });

  const TABS: { id: Tab; label: string; icon: any }[] = [
    { id: "enroll", label: "Enroll", icon: Fingerprint },
    { id: "devices", label: `Devices${devices.length ? ` (${devices.length})` : ""}`, icon: Smartphone },
    { id: "security", label: "Security", icon: Shield },
    { id: "pay", label: "Pay Demo", icon: CreditCard },
  ];

  return (
    <div className="min-h-screen p-6 max-w-2xl mx-auto">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-7">
        <div className="flex items-center gap-3 mb-1">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, rgba(129,140,248,0.2) 0%, rgba(0,229,168,0.15) 100%)", border: "1px solid rgba(129,140,248,0.3)" }}
          >
            <Fingerprint size={20} className="text-[#818cf8]" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Fingerprint Security Center</h1>
            <p className="text-xs text-white/40">Hardware-backed WebAuthn authentication</p>
          </div>
          <div className="ml-auto flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full" style={{ background: "rgba(0,229,168,0.1)", border: "1px solid rgba(0,229,168,0.25)", color: "#00E5A8" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A8] animate-pulse" />
            FIDO2 · WebAuthn
          </div>
        </div>

        {/* Security status */}
        {!isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-4 flex items-center gap-2.5 rounded-xl px-4 py-3"
            style={hasActiveDevices
              ? { background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.2)" }
              : { background: "rgba(251,191,36,0.06)", border: "1px solid rgba(251,191,36,0.2)" }}
          >
            {hasActiveDevices
              ? <ShieldCheck size={16} className="text-[#00E5A8] shrink-0" />
              : <AlertTriangle size={16} className="text-[#fbbf24] shrink-0" />}
            <p className="text-xs" style={{ color: hasActiveDevices ? "#00E5A8" : "#fbbf24" }}>
              {hasActiveDevices
                ? `${devices.filter(d => d.is_active).length} device${devices.filter(d => d.is_active).length !== 1 ? "s" : ""} enrolled · Fingerprint payments active`
                : "No fingerprint device enrolled · Enroll to enable biometric payments"}
            </p>
          </motion.div>
        )}
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 rounded-xl bg-white/4 border border-white/8">
        {TABS.map(t => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              id={`tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className="relative flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-medium transition-colors"
              style={{ color: active ? "white" : "rgba(255,255,255,0.4)" }}
            >
              {active && (
                <motion.div
                  layoutId="tab-bg"
                  className="absolute inset-0 rounded-lg"
                  style={{ background: "linear-gradient(135deg, rgba(129,140,248,0.25) 0%, rgba(0,229,168,0.15) 100%)", border: "1px solid rgba(129,140,248,0.3)" }}
                />
              )}
              <Icon size={13} className="relative z-10" />
              <span className="relative z-10 hidden sm:inline">{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.18 }}
          className="rounded-2xl border border-white/8 p-5"
          style={{ background: "rgba(255,255,255,0.03)" }}
        >
          {tab === "enroll" && (
            <>
              <p className="text-sm font-semibold text-white mb-1">Enroll New Device</p>
              <p className="text-xs text-white/40 mb-5">Your fingerprint private key never leaves this device. NeoFace stores only a cryptographic public key.</p>
              <EnrollFlow onSuccess={() => { qc.invalidateQueries({ queryKey: ["webauthn-devices"] }); setTab("devices"); }} />
            </>
          )}

          {tab === "devices" && (
            <>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-white">Enrolled Devices</p>
                  <p className="text-xs text-white/40">{devices.length} device{devices.length !== 1 ? "s" : ""} · {devices.filter(d => d.is_active).length} active</p>
                </div>
                <button
                  onClick={() => setTab("enroll")}
                  className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg transition-colors"
                  style={{ background: "rgba(129,140,248,0.15)", color: "#818cf8", border: "1px solid rgba(129,140,248,0.25)" }}
                >
                  <Fingerprint size={12} /> Enroll New
                </button>
              </div>

              {isLoading ? (
                <div className="flex justify-center py-10">
                  <motion.div className="w-8 h-8 rounded-full border-2 border-[#818cf8] border-t-transparent" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }} />
                </div>
              ) : devices.length === 0 ? (
                <div className="flex flex-col items-center gap-3 py-10 text-center">
                  <Fingerprint size={32} className="text-white/15" />
                  <p className="text-sm text-white/40">No devices enrolled yet</p>
                  <button onClick={() => setTab("enroll")} className="text-xs text-[#818cf8] hover:underline flex items-center gap-1">
                    Enroll a device <ChevronRight size={11} />
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <AnimatePresence>
                    {devices.map(d => (
                      <DeviceCard
                        key={d.id}
                        device={d}
                        onRevoke={id => revokeMutation.mutate(id)}
                        onRename={(id, name) => renameMutation.mutate({ id, name })}
                        onTogglePayments={(id, enabled) => toggleMutation.mutate({ id, enabled })}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              )}
            </>
          )}

          {tab === "security" && <SecurityCenter devices={devices} />}

          {tab === "pay" && <PaymentDemo hasDevices={hasActiveDevices} />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
