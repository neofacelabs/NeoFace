"use client";
import { useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck, Scan, Eye, Fingerprint, ArrowRight, CheckCircle2,
  Camera, Upload, Loader2, X, Zap, Star, AlertCircle, CreditCard,
} from "lucide-react";
import Image from "next/image";
import { paymentsApi } from "@/lib/api";
import { cn, extractErrorMsg } from "@/lib/utils";
import { toast } from "sonner";

/* ── Mock product ─────────────────────────────────────────────────────────── */
const PRODUCT = {
  name: "MacBook Pro 16\"",
  spec: "M4 Max · 128GB RAM · 4TB SSD · Space Black",
  price: 3499.00,
  imgUrl: "https://store.storeimages.cdn-apple.com/1/as-images.apple.com/is/mbp16-spacegray-gallery1-202410_GEO_US?wid=2000&hei=1536&fmt=jpeg&qlt=95&.v=UXp0U0lLc1pYMXIxZjBVbHBReGl4dGpheE1aOEQwM0E5aTBuMEZLdEllT1Nicjh2ZVlNN0pVVXhpbXdTb3Q2S0lZek1NZzJ6UEJFWXhXL2V3M3BXMU9ZQWZ3Z3pGSnJJT0ZuSVQ5RDBnM0E",
};

/* ── Face capture inside modal ────────────────────────────────────────────── */
function ModalFaceCapture({ onCapture }: { onCapture: (blob: Blob) => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [streaming, setStreaming] = useState(false);
  const [captured, setCaptured] = useState(false);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
      if (videoRef.current) { videoRef.current.srcObject = stream; setStreaming(true); }
    } catch { toast.error("Camera permission denied"); }
  };

  const captureFrame = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const ctx = canvasRef.current.getContext("2d")!;
    canvasRef.current.width = videoRef.current.videoWidth;
    canvasRef.current.height = videoRef.current.videoHeight;
    ctx.drawImage(videoRef.current, 0, 0);
    setCaptured(true);
    (videoRef.current.srcObject as MediaStream)?.getTracks().forEach(t => t.stop());
    setStreaming(false);
    canvasRef.current.toBlob(blob => blob && onCapture(blob), "image/jpeg", 0.9);
  };

  return (
    <div className="space-y-3">
      <div className="relative rounded-xl overflow-hidden bg-black w-full" style={{ aspectRatio: "4/3" }}>
        <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
        <canvas ref={canvasRef} className="hidden" />
        {!streaming && !captured && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2"
            style={{ background: "rgba(0,0,0,0.8)" }}>
            <Camera size={24} style={{ color: "rgba(255,255,255,0.2)" }} />
            <p className="text-[11px] text-[rgba(255,255,255,0.3)]">Press Start to activate camera</p>
          </div>
        )}
        {streaming && (
          <>
            <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 640 480">
              <ellipse cx="320" cy="240" rx="130" ry="165" fill="none" stroke="rgba(0,229,168,0.7)" strokeWidth="2" strokeDasharray="8 5" />
            </svg>
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9.5px] font-semibold"
              style={{ background: "rgba(0,0,0,0.7)", color: "#00E5A8" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-[#00E5A8]" style={{ animation: "pulse 1s infinite" }} />
              LIVE DETECTION
            </div>
          </>
        )}
        {captured && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2"
            style={{ background: "rgba(0,229,168,0.12)" }}>
            <CheckCircle2 size={28} style={{ color: "#00E5A8" }} />
            <p className="text-[12px] font-semibold text-white">Face Captured</p>
          </div>
        )}
      </div>
      {!captured && (
        <button
          onClick={streaming ? captureFrame : startCamera}
          className="w-full py-2.5 rounded-xl text-[12.5px] font-semibold flex items-center justify-center gap-2 transition-all"
          style={{ background: "rgba(0,229,168,0.12)", border: "1px solid rgba(0,229,168,0.3)", color: "#00E5A8" }}
        >
          <Scan size={14} />
          {streaming ? "Capture Face" : "Start Camera"}
        </button>
      )}
    </div>
  );
}

/* ── Biometric modal ──────────────────────────────────────────────────────── */
interface ModalProps {
  amount: number;
  onClose: () => void;
  onSuccess: (result: any) => void;
}
function BiometricModal({ amount, onClose, onSuccess }: ModalProps) {
  const [step, setStep] = useState<"face" | "iris" | "fingerprint" | "processing">("face");
  const [faceBlob, setFaceBlob] = useState<Blob | null>(null);
  const [irisFile, setIrisFile] = useState<File | null>(null);
  const [fpFile, setFpFile] = useState<File | null>(null);
  const irisRef = useRef<HTMLInputElement>(null);
  const fpRef = useRef<HTMLInputElement>(null);

  const isHighValue = amount >= 1000;

  const authorize = async () => {
    setStep("processing");
    try {
      const fd = new FormData();
      if (faceBlob) fd.append("face_image", faceBlob, "face.jpg");
      if (irisFile) fd.append("iris_image", irisFile);
      if (fpFile) fd.append("fingerprint_image", fpFile);
      fd.append("amount", String(amount));
      fd.append("currency", "USD");
      fd.append("modality", irisFile || fpFile ? "multi_modal" : "face");

      const res = await paymentsApi.authorize(fd);
      onSuccess(res.data);
    } catch (e: any) {
      toast.error(extractErrorMsg(e, "Payment authorization failed"));
    } finally {
      onClose();
    }
  };

  const steps = isHighValue
    ? ["face", "iris", "fingerprint"] as const
    : ["face"] as const;

  const stepDefs = {
    face: { icon: Scan, color: "#00E5A8", label: "Face Scan", desc: "Look directly at the camera" },
    iris: { icon: Eye, color: "#00C2FF", label: "Iris Scan", desc: "Upload close-up eye image" },
    fingerprint: { icon: Fingerprint, color: "#818cf8", label: "Fingerprint", desc: "Upload fingerprint scan" },
  };
  const currentStep = stepDefs[step as keyof typeof stepDefs];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.85)", backdropFilter: "blur(16px)" }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.93, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.93 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-sm rounded-3xl overflow-hidden"
        style={{ background: "rgba(8,8,8,0.99)", border: "1px solid rgba(255,255,255,0.09)", boxShadow: "0 32px 100px rgba(0,0,0,0.8)" }}
      >
        {/* Header */}
        <div className="relative p-5 pb-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="absolute top-0 left-1/4 right-1/4 h-px"
            style={{ background: "linear-gradient(90deg, transparent, rgba(0,229,168,0.4), transparent)" }} />
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center"
                style={{ background: "rgba(0,229,168,0.1)", border: "1px solid rgba(0,229,168,0.2)" }}>
                <ShieldCheck size={15} style={{ color: "#00E5A8" }} />
              </div>
              <div>
                <p className="text-[13px] font-semibold text-white">NeoFace Pay</p>
                <p className="text-[10px] text-[rgba(255,255,255,0.3)]">Biometric Authorization</p>
              </div>
            </div>
            <button onClick={onClose} className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
              style={{ background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.4)" }}>
              <X size={14} />
            </button>
          </div>

          {/* Amount */}
          <div className="mt-4 text-center">
            <p className="text-[11px] text-[rgba(255,255,255,0.3)] mb-0.5">Authorizing payment</p>
            <p className="text-[36px] font-bold tracking-tight text-white">${amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}</p>
            {isHighValue && (
              <div className="flex items-center justify-center gap-1.5 mt-2">
                <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[9.5px] font-semibold"
                  style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.25)", color: "#f59e0b" }}>
                  <Zap size={8} />
                  HIGH VALUE — MULTI-MODAL REQUIRED
                </div>
              </div>
            )}
          </div>

          {/* Step progress */}
          <div className="flex gap-1.5 mt-4">
            {steps.map((s, i) => {
              const sd = stepDefs[s];
              const isActive = s === step;
              const isDone = steps.indexOf(step as any) > i;
              return (
                <div key={s} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full h-0.5 rounded-full transition-all duration-500"
                    style={{ background: isDone ? sd.color : isActive ? sd.color : "rgba(255,255,255,0.08)" }} />
                  <div className="flex items-center gap-1">
                    <sd.icon size={9} style={{ color: isDone || isActive ? sd.color : "rgba(255,255,255,0.2)" }} />
                    <span className="text-[9px]" style={{ color: isDone || isActive ? sd.color : "rgba(255,255,255,0.2)" }}>{sd.label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Body */}
        <div className="p-5">
          <AnimatePresence mode="wait">
            {step === "processing" ? (
              <motion.div key="processing"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center gap-4 py-8"
              >
                <div className="relative w-16 h-16">
                  <div className="absolute inset-0 rounded-full"
                    style={{ border: "2px solid rgba(0,229,168,0.1)" }} />
                  <div className="absolute inset-0 rounded-full animate-spin"
                    style={{ border: "2px solid transparent", borderTopColor: "#00E5A8" }} />
                  <div className="absolute inset-2 rounded-full flex items-center justify-center"
                    style={{ background: "rgba(0,229,168,0.08)" }}>
                    <ShieldCheck size={20} style={{ color: "#00E5A8" }} />
                  </div>
                </div>
                <div className="text-center">
                  <p className="text-[14px] font-semibold text-white">Authorizing…</p>
                  <p className="text-[11px] text-[rgba(255,255,255,0.35)] mt-1">Running biometric fusion engine</p>
                </div>
                <div className="w-full space-y-2 mt-2">
                  {["Identity verification", "Liveness detection", "Fusion scoring"].map((t, i) => (
                    <motion.div key={t}
                      initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.3 }}
                      className="flex items-center gap-2 text-[11px]"
                      style={{ color: "rgba(255,255,255,0.3)" }}>
                      <Loader2 size={10} className="animate-spin shrink-0" style={{ color: "#00E5A8" }} />
                      {t}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div key={step}
                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }} transition={{ duration: 0.25 }}
              >
                {step === "face" && (
                  <div className="space-y-3">
                    <ModalFaceCapture onCapture={blob => setFaceBlob(blob)} />
                    <button
                      onClick={() => isHighValue ? setStep("iris") : authorize()}
                      disabled={!faceBlob}
                      className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-[13px] font-semibold transition-all"
                      style={{
                        background: faceBlob ? "rgba(0,229,168,0.15)" : "rgba(255,255,255,0.04)",
                        border: `1px solid ${faceBlob ? "rgba(0,229,168,0.35)" : "rgba(255,255,255,0.08)"}`,
                        color: faceBlob ? "#00E5A8" : "rgba(255,255,255,0.2)",
                        cursor: faceBlob ? "pointer" : "not-allowed",
                      }}>
                      {isHighValue ? <><ArrowRight size={14} /> Continue to Iris Scan</> : <><ShieldCheck size={14} /> Authorize ${amount.toFixed(2)}</>}
                    </button>
                  </div>
                )}

                {step === "iris" && (
                  <div className="space-y-3">
                    <div
                      className="rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer transition-all"
                      style={{ aspectRatio: "4/3", background: irisFile ? "rgba(0,194,255,0.06)" : "rgba(255,255,255,0.02)", border: `1.5px dashed ${irisFile ? "rgba(0,194,255,0.4)" : "rgba(255,255,255,0.1)"}` }}
                      onClick={() => irisRef.current?.click()}
                    >
                      {irisFile ? (
                        <div className="flex flex-col items-center gap-2">
                          <CheckCircle2 size={24} style={{ color: "#00C2FF" }} />
                          <p className="text-[12px] font-medium" style={{ color: "#00C2FF" }}>{irisFile.name}</p>
                        </div>
                      ) : (
                        <>
                          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ background: "rgba(0,194,255,0.1)", border: "1px solid rgba(0,194,255,0.2)" }}>
                            <Upload size={18} style={{ color: "#00C2FF" }} />
                          </div>
                          <div className="text-center">
                            <p className="text-[12px] font-medium text-white">Drop Iris Image</p>
                            <p className="text-[10px] text-[rgba(255,255,255,0.3)] mt-0.5">Close-up eye scan · JPG, PNG</p>
                          </div>
                        </>
                      )}
                      <input ref={irisRef} type="file" accept="image/*" className="hidden"
                        onChange={e => e.target.files?.[0] && setIrisFile(e.target.files[0])} />
                    </div>
                    <button
                      onClick={() => setStep("fingerprint")}
                      disabled={!irisFile}
                      className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-[13px] font-semibold transition-all"
                      style={{
                        background: irisFile ? "rgba(0,194,255,0.12)" : "rgba(255,255,255,0.04)",
                        border: `1px solid ${irisFile ? "rgba(0,194,255,0.3)" : "rgba(255,255,255,0.08)"}`,
                        color: irisFile ? "#00C2FF" : "rgba(255,255,255,0.2)",
                        cursor: irisFile ? "pointer" : "not-allowed",
                      }}>
                      <ArrowRight size={14} /> Continue to Fingerprint
                    </button>
                  </div>
                )}

                {step === "fingerprint" && (
                  <div className="space-y-3">
                    <div
                      className="rounded-xl flex flex-col items-center justify-center gap-3 cursor-pointer transition-all"
                      style={{ aspectRatio: "4/3", background: fpFile ? "rgba(129,140,248,0.06)" : "rgba(255,255,255,0.02)", border: `1.5px dashed ${fpFile ? "rgba(129,140,248,0.4)" : "rgba(255,255,255,0.1)"}` }}
                      onClick={() => fpRef.current?.click()}
                    >
                      {fpFile ? (
                        <div className="flex flex-col items-center gap-2">
                          <CheckCircle2 size={24} style={{ color: "#818cf8" }} />
                          <p className="text-[12px] font-medium" style={{ color: "#818cf8" }}>{fpFile.name}</p>
                        </div>
                      ) : (
                        <>
                          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ background: "rgba(129,140,248,0.1)", border: "1px solid rgba(129,140,248,0.2)" }}>
                            <Upload size={18} style={{ color: "#818cf8" }} />
                          </div>
                          <div className="text-center">
                            <p className="text-[12px] font-medium text-white">Drop Fingerprint Image</p>
                            <p className="text-[10px] text-[rgba(255,255,255,0.3)] mt-0.5">Scanner capture · JPG, PNG</p>
                          </div>
                        </>
                      )}
                      <input ref={fpRef} type="file" accept="image/*" className="hidden"
                        onChange={e => e.target.files?.[0] && setFpFile(e.target.files[0])} />
                    </div>
                    <button
                      onClick={authorize}
                      disabled={!fpFile}
                      className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-[13px] font-semibold transition-all"
                      style={{
                        background: fpFile ? "rgba(129,140,248,0.12)" : "rgba(255,255,255,0.04)",
                        border: `1px solid ${fpFile ? "rgba(129,140,248,0.3)" : "rgba(255,255,255,0.08)"}`,
                        color: fpFile ? "#818cf8" : "rgba(255,255,255,0.2)",
                        cursor: fpFile ? "pointer" : "not-allowed",
                      }}>
                      <ShieldCheck size={14} /> Authorize ${amount.toFixed(2)}
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}

/* ── Success screen ────────────────────────────────────────────────────────── */
function SuccessScreen({ result, amount, onReset }: { result: any; amount: number; onReset: () => void }) {
  const fusionScore = result?.fusion_score ?? result?.confidence_score ?? 0.97;
  const modalities = result?.modalities_used ?? ["face"];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 py-16"
    >
      {/* Animated checkmark ring */}
      <div className="relative">
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="w-24 h-24 rounded-full flex items-center justify-center"
          style={{ background: "rgba(0,229,168,0.12)", border: "2px solid rgba(0,229,168,0.3)", boxShadow: "0 0 50px rgba(0,229,168,0.2)" }}
        >
          <motion.div
            initial={{ scale: 0 }} animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 300, delay: 0.15 }}>
            <CheckCircle2 size={40} style={{ color: "#00E5A8" }} />
          </motion.div>
        </motion.div>
        {/* Ripple rings */}
        {[1, 2, 3].map(i => (
          <motion.div key={i}
            className="absolute inset-0 rounded-full"
            style={{ border: "1px solid rgba(0,229,168,0.3)" }}
            initial={{ scale: 1, opacity: 0.6 }}
            animate={{ scale: 1 + i * 0.4, opacity: 0 }}
            transition={{ duration: 1.5, delay: i * 0.2, repeat: Infinity, ease: "easeOut" }}
          />
        ))}
      </div>

      <div className="text-center">
        <motion.p
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
          className="text-[28px] font-bold text-white tracking-tight">
          Payment Authorized
        </motion.p>
        <motion.p
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
          className="text-[40px] font-bold mt-1" style={{ color: "#00E5A8" }}>
          ${amount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
        </motion.p>
        <motion.p
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
          className="text-[13px] text-[rgba(255,255,255,0.35)] mt-2">
          Identity verified · No card needed · No password
        </motion.p>
      </div>

      {/* Fusion breakdown */}
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
        className="w-full max-w-xs rounded-2xl p-4 space-y-3"
        style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}
      >
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-[rgba(255,255,255,0.4)] font-medium">Fusion Score</span>
          <span className="font-bold" style={{ color: "#00E5A8" }}>{(fusionScore * 100).toFixed(1)}%</span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
          <motion.div
            initial={{ width: 0 }} animate={{ width: `${fusionScore * 100}%` }}
            transition={{ duration: 0.8, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
            className="h-full rounded-full" style={{ background: "linear-gradient(90deg, #818cf8, #00C2FF, #00E5A8)" }}
          />
        </div>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {modalities.map((m: string) => {
            const colors: Record<string, string> = { face: "#00E5A8", iris: "#00C2FF", fingerprint: "#818cf8" };
            const icons: Record<string, any> = { face: Scan, iris: Eye, fingerprint: Fingerprint };
            const Icon = icons[m] ?? ShieldCheck;
            const color = colors[m] ?? "#ffffff";
            return (
              <div key={m} className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold"
                style={{ background: `${color}12`, border: `1px solid ${color}25`, color }}>
                <Icon size={9} />
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </div>
            );
          })}
        </div>
      </motion.div>

      <motion.button
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }}
        onClick={onReset}
        className="px-6 py-2.5 rounded-xl text-[13px] font-medium transition-all"
        style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "rgba(255,255,255,0.5)" }}
        whileHover={{ borderColor: "rgba(0,229,168,0.3)", color: "white" }}>
        Try Another Payment
      </motion.button>
    </motion.div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────────────── */
export default function CheckoutDemoPage() {
  const [showBiometric, setShowBiometric] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [customAmount, setCustomAmount] = useState(PRODUCT.price);

  if (result) {
    return (
      <div className="min-h-screen bg-black px-4">
        <div className="max-w-2xl mx-auto pt-16">
          <div className="text-center mb-8">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Image src="/logo.png" alt="NeoFace Logo" width={200} height={60} className="h-10 w-auto object-contain" />
            </div>
          </div>
          <SuccessScreen result={result} amount={customAmount} onReset={() => setResult(null)} />
        </div>
      </div>
    );
  }

  return (
    <>
      <AnimatePresence>
        {showBiometric && (
          <BiometricModal
            amount={customAmount}
            onClose={() => setShowBiometric(false)}
            onSuccess={data => { setShowBiometric(false); setResult(data); }}
          />
        )}
      </AnimatePresence>

      <div className="min-h-screen bg-black">
        {/* Subtle grid */}
        <div className="fixed inset-0 pointer-events-none"
          style={{ backgroundImage: "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)", backgroundSize: "60px 60px" }} />

        {/* Mock store nav */}
        <nav className="relative border-b" style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(0,0,0,0.9)", backdropFilter: "blur(12px)" }}>
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Image src="/logo.png" alt="NeoFace Logo" width={200} height={60} className="h-10 w-auto object-contain" />
              <span className="text-[12px] font-semibold text-white ml-2">Store Demo</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9.5px] font-semibold"
              style={{ background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.15)", color: "#00E5A8" }}>
              <Zap size={8} />
              SANDBOX MODE
            </div>
          </div>
        </nav>

        {/* Main checkout layout */}
        <div className="relative max-w-6xl mx-auto px-6 py-12">
          <div className="grid lg:grid-cols-2 gap-12 items-start">

            {/* Product side */}
            <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}>
              <div className="rounded-3xl overflow-hidden mb-6"
                style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <div className="bg-gradient-to-br from-[#1a1a2e] to-[#0d0d0d] p-8 flex items-center justify-center" style={{ minHeight: 280 }}>
                  {/* Stylized product box instead of potentially-broken external image */}
                  <div className="flex flex-col items-center gap-4">
                    <div className="w-32 h-20 rounded-2xl flex items-center justify-center"
                      style={{ background: "linear-gradient(135deg, #2a2a2a, #1a1a1a)", border: "1px solid rgba(255,255,255,0.12)", boxShadow: "0 20px 60px rgba(0,0,0,0.6)" }}>
                      <div className="w-2 h-12 rounded-full" style={{ background: "rgba(255,255,255,0.15)" }} />
                    </div>
                    <div className="w-40 h-3 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }} />
                  </div>
                </div>
                <div className="p-5">
                  <p className="text-[11px] text-[rgba(255,255,255,0.35)] uppercase tracking-wider mb-1">New · Space Black</p>
                  <h2 className="text-[18px] font-semibold text-white">{PRODUCT.name}</h2>
                  <p className="text-[12px] text-[rgba(255,255,255,0.3)] mt-0.5">{PRODUCT.spec}</p>
                </div>
              </div>

              {/* Trust badges */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { icon: ShieldCheck, label: "Biometric Secured", color: "#00E5A8" },
                  { icon: Zap, label: "Instant Auth", color: "#00C2FF" },
                  { icon: Star, label: "No Card Needed", color: "#818cf8" },
                ].map(b => (
                  <div key={b.label} className="flex flex-col items-center gap-1.5 p-3 rounded-xl text-center"
                    style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <b.icon size={14} style={{ color: b.color }} />
                    <p className="text-[9.5px] text-[rgba(255,255,255,0.35)] font-medium leading-tight">{b.label}</p>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Order summary / payment side */}
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="space-y-4"
            >
              <div>
                <h1 className="text-[22px] font-bold text-white tracking-tight">Order Summary</h1>
                <p className="text-[13px] text-[rgba(255,255,255,0.3)] mt-0.5">Review your purchase before authorizing</p>
              </div>

              {/* Line items */}
              <div className="rounded-2xl overflow-hidden" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)" }}>
                {[
                  { label: PRODUCT.name, value: PRODUCT.price },
                  { label: "AppleCare+ (3yr)", value: 299 },
                  { label: "Tax (8.5%)", value: Math.round(PRODUCT.price * 0.085) },
                ].map((line, i, arr) => (
                  <div key={line.label}
                    className="flex items-center justify-between px-4 py-3 text-[13px]"
                    style={{ borderBottom: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                    <span className="text-[rgba(255,255,255,0.5)]">{line.label}</span>
                    <span className="font-medium text-white">${line.value.toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
                  </div>
                ))}
                <div className="flex items-center justify-between px-4 py-3 text-[14px]"
                  style={{ borderTop: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.02)" }}>
                  <span className="font-semibold text-white">Total</span>
                  <span className="font-bold" style={{ color: "#00E5A8" }}>
                    ${(PRODUCT.price + 299 + Math.round(PRODUCT.price * 0.085)).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </span>
                </div>
              </div>

              {/* Amount selector */}
              <div className="rounded-2xl p-4 space-y-2"
                style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.07)" }}>
                <label className="text-[11px] text-[rgba(255,255,255,0.4)] font-medium uppercase tracking-wider block">Demo Amount</label>
                <div className="flex gap-2 flex-wrap">
                  {[50, 500, 1000, PRODUCT.price].map(amt => (
                    <button key={amt}
                      onClick={() => setCustomAmount(amt)}
                      className="px-3 py-1.5 rounded-lg text-[11.5px] font-medium transition-all"
                      style={{
                        background: customAmount === amt ? "rgba(0,194,255,0.12)" : "rgba(255,255,255,0.04)",
                        border: `1px solid ${customAmount === amt ? "rgba(0,194,255,0.3)" : "rgba(255,255,255,0.08)"}`,
                        color: customAmount === amt ? "#00C2FF" : "rgba(255,255,255,0.4)",
                      }}>
                      ${amt.toLocaleString()}
                    </button>
                  ))}
                </div>
                <p className="text-[10px] text-[rgba(255,255,255,0.25)]">
                  {customAmount >= 1000 ? "⚠ High-value: Multi-modal (Face + Iris + Fingerprint) required" : "Standard: Face recognition only"}
                </p>
              </div>

              {/* The main button */}
              <motion.button
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                onClick={() => setShowBiometric(true)}
                className="w-full relative overflow-hidden py-4 rounded-2xl font-semibold text-[15px] transition-all"
                style={{
                  background: "linear-gradient(135deg, rgba(0,229,168,0.15), rgba(0,194,255,0.1))",
                  border: "1px solid rgba(0,229,168,0.35)",
                  color: "#00E5A8",
                  boxShadow: "0 0 40px rgba(0,229,168,0.08)",
                }}
              >
                <div className="absolute inset-0 pointer-events-none"
                  style={{ background: "linear-gradient(135deg, rgba(0,229,168,0.05), transparent)" }} />
                <span className="relative flex items-center justify-center gap-3">
                  <div className="w-5 h-5 rounded-md flex items-center justify-center"
                    style={{ background: "rgba(0,229,168,0.2)", border: "1px solid rgba(0,229,168,0.3)" }}>
                    <svg width="11" height="11" viewBox="0 0 32 32" fill="none">
                      <ellipse cx="16" cy="14" rx="5.5" ry="6.5" stroke="#00E5A8" strokeWidth="1.5" fill="none" />
                      <circle cx="16" cy="14" r="1.1" fill="#00E5A8" />
                    </svg>
                  </div>
                  Pay with NeoFace — ${customAmount.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </span>
              </motion.button>

              {/* OR divider with card */}
              <div className="relative flex items-center gap-3 py-1">
                <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
                <p className="text-[10.5px] text-[rgba(255,255,255,0.2)]">or pay traditionally</p>
                <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
              </div>

              <button className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-[13px] font-medium transition-all"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.25)" }}
                onClick={() => toast("This demo showcases NeoFace — biometric checkout only. No card flow built.", { icon: "💳" })}>
                <CreditCard size={14} />
                Pay with Card
              </button>

              <p className="text-[10.5px] text-center text-[rgba(255,255,255,0.2)] leading-relaxed">
                By authorizing, your biometric identity verifies this transaction.<br />
                No card, no PIN, no password.
              </p>
            </motion.div>
          </div>
        </div>
      </div>
    </>
  );
}
