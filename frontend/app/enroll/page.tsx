"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { User, Mail, ChevronRight, Upload, CheckCircle2, RefreshCw, X, AlertCircle, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { enrollmentApi } from "@/lib/api";
import { useEnrollmentStore } from "@/store/enrollment";
import { cn, extractErrorMsg } from "@/lib/utils";
import type { EnrollmentResponse } from "@/types";

const metaSchema = z.object({
  name: z.string().min(2, "Name required"),
  email: z.string().email("Valid email required"),
  phone: z.string().optional(),
});
type MetaForm = z.infer<typeof metaSchema>;

const STEPS = ["Identity", "Capture", "Review", "Complete"];

function StepDots({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-3 mb-10">
      {STEPS.map((label, i) => {
        const idx = i + 1;
        const done = current > idx;
        const active = current === idx;
        return (
          <div key={label} className="flex items-center gap-2">
            <div className={cn(
              "flex items-center justify-center rounded-full text-[11px] font-semibold transition-all duration-300",
              "w-6 h-6",
              done   ? "bg-[#34d399] text-black"    :
              active ? "bg-[rgba(124,124,255,0.9)] text-white shadow-glow-xs" :
              "bg-[rgba(255,255,255,0.05)] text-[rgba(255,255,255,0.3)] border border-[rgba(255,255,255,0.08)]"
            )}>
              {done ? <CheckCircle2 size={12} /> : idx}
            </div>
            <span className={cn("text-[12px] font-medium hidden sm:block", active ? "text-white" : "text-[rgba(255,255,255,0.3)]")}>
              {label}
            </span>
            {i < STEPS.length - 1 && (
              <div className={cn("w-8 h-px ml-1", current > idx ? "bg-[#34d399]/40" : "bg-[rgba(255,255,255,0.07)]")} />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Step 1 ── */
function StepInfo({ onNext }: { onNext: (d: MetaForm) => void }) {
  const { register, handleSubmit, formState: { errors } } = useForm<MetaForm>({ resolver: zodResolver(metaSchema) });
  return (
    <motion.div key="info" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1 tracking-tight">Your identity</h2>
        <p className="text-[13px] text-[rgba(255,255,255,0.38)]">This metadata links to your biometric profile.</p>
      </div>
      <form onSubmit={handleSubmit(onNext)} className="space-y-4">
        <Input label="Full Name" placeholder="Alex Johnson" icon={<User size={14} />} error={errors.name?.message} {...register("name")} />
        <Input label="Email" type="email" placeholder="you@company.com" icon={<Mail size={14} />} error={errors.email?.message} {...register("email")} />
        <Input label="Phone (optional)" placeholder="+1 555 000 0000" {...register("phone")} />
        <button type="submit" className="w-full btn-accent py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 group mt-1">
          Continue <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
        </button>
      </form>
    </motion.div>
  );
}

/* ── Step 2 ── */
function StepCapture({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [ready, setReady] = useState(false);
  const [camErr, setCamErr] = useState<string>();
  const [countdown, setCountdown] = useState<number | null>(null);
  const { capturedImages, addImage, resetImages } = useEnrollmentStore();

  const startCam = useCallback(async () => {
    setCamErr(undefined);
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } } });
      streamRef.current = s;
      if (videoRef.current) { videoRef.current.srcObject = s; videoRef.current.onloadedmetadata = () => { videoRef.current?.play(); setReady(true); }; }
    } catch { setCamErr("Camera access denied. Please allow camera permissions."); }
  }, []);

  const stopCam = useCallback(() => { streamRef.current?.getTracks().forEach(t => t.stop()); setReady(false); }, []);

  useEffect(() => { startCam(); return stopCam; }, [startCam, stopCam]);

  const [validating, setValidating] = useState(false);

  const capture = useCallback(() => {
    if (!videoRef.current || !canvasRef.current || !ready || capturedImages.length >= 5 || validating) return;
    const v = videoRef.current; const c = canvasRef.current;
    c.width = v.videoWidth; c.height = v.videoHeight;
    const ctx = c.getContext("2d")!;
    ctx.drawImage(v, 0, 0);
    const dataUrl = c.toDataURL("image/jpeg", 0.9);

    setValidating(true);
    const toastId = toast.loading(`Validating face image ${capturedImages.length + 1}...`);

    c.toBlob(async (blob) => {
      if (!blob) {
        toast.error("Failed to process captured frame.", { id: toastId });
        setValidating(false);
        return;
      }
      try {
        const fd = new FormData();
        fd.append("file", blob, "face.jpg");
        const res = await enrollmentApi.validateFrame(fd);
        if (res.data && res.data.success) {
          addImage(dataUrl);
          toast.success(`Image ${capturedImages.length + 1} captured & validated successfully!`, { id: toastId });
        } else {
          const errMsg = res.data?.error || "No valid face detected. Please ensure exactly one clear face is visible.";
          toast.error(errMsg, { id: toastId });
        }
      } catch (err: any) {
        const errMsg = extractErrorMsg(err, "Frame validation failed. Please check your webcam and lighting.");
        toast.error(errMsg, { id: toastId });
      } finally {
        setValidating(false);
      }
    }, "image/jpeg", 0.9);
  }, [ready, capturedImages.length, addImage, validating]);

  const startCountdown = () => {
    let n = 3; setCountdown(n);
    const tick = () => { n--; if (n <= 0) { setCountdown(null); capture(); } else { setCountdown(n); setTimeout(tick, 1000); } };
    setTimeout(tick, 1000);
  };

  return (
    <motion.div key="capture" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1 tracking-tight">Capture your face</h2>
        <p className="text-[13px] text-[rgba(255,255,255,0.38)]">1–5 photos. Look slightly left, right, and straight ahead.</p>
      </div>

      {/* Webcam */}
      <div className="relative rounded-2xl overflow-hidden bg-[rgba(255,255,255,0.02)] border border-[rgba(255,255,255,0.07)] aspect-[4/3] webcam-mirror">
        {camErr ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-8">
            <AlertCircle size={32} className="text-[#f87171]/60" />
            <p className="text-[13px] text-[rgba(255,255,255,0.4)] text-center">{camErr}</p>
            <button onClick={startCam} className="btn-primary px-4 py-2 rounded-xl text-sm text-white">Retry</button>
          </div>
        ) : (
          <>
            <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />

            {/* Face oval */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="relative w-44 h-56">
                <div className={cn("absolute inset-0 rounded-full border-2 transition-colors duration-300", ready ? "border-[rgba(124,124,255,0.7)]" : "border-[rgba(255,255,255,0.2)]")} />
                {ready && <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-[#a5b4fc] to-transparent scan-line" />}
                {[["top-0 left-0","border-t border-l"], ["top-0 right-0","border-t border-r"], ["bottom-0 left-0","border-b border-l"], ["bottom-0 right-0","border-b border-r"]].map(([pos, border], i) => (
                  <div key={i} className={`absolute w-4 h-4 ${pos} ${border} border-[#a5b4fc]`} />
                ))}
              </div>
            </div>

            {/* Countdown */}
            <AnimatePresence>
              {countdown !== null && (
                <motion.div initial={{ opacity: 0, scale: 2 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0 }}
                  className="absolute inset-0 flex items-center justify-center bg-black/50">
                  <span className="text-8xl font-black text-white drop-shadow-lg">{countdown}</span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Status */}
            <div className="absolute top-3 left-3">
              <div className={cn("flex items-center gap-1.5 text-[11px] rounded-full px-2.5 py-1", "bg-[rgba(0,0,0,0.6)] backdrop-blur-sm border border-[rgba(255,255,255,0.08)]",
                ready ? "text-[#34d399]" : "text-[rgba(255,255,255,0.4)]")}>
                <span className={cn("w-1.5 h-1.5 rounded-full", ready ? "bg-[#34d399] animate-pulse" : "bg-[rgba(255,255,255,0.3)]")} />
                {ready ? "Camera ready" : "Starting…"}
              </div>
            </div>

            {/* Capture button */}
            <div className="absolute bottom-4 inset-x-0 flex items-center justify-center gap-4">
              <span className="text-[11px] text-white/50 bg-black/50 backdrop-blur-sm px-2.5 py-1 rounded-full">
                {capturedImages.length}/5
              </span>
              <button
                onClick={startCountdown}
                disabled={!ready || capturedImages.length >= 5 || validating}
                className={cn(
                  "w-14 h-14 rounded-full border-4 border-white/80 flex items-center justify-center transition-all duration-200 active:scale-95",
                  (!ready || capturedImages.length >= 5 || validating) ? "opacity-40 cursor-not-allowed" : "hover:border-white cursor-pointer ring-pulse"
                )}
              >
                {validating ? (
                  <RefreshCw size={18} className="animate-spin text-white" />
                ) : (
                  <div className="w-9 h-9 rounded-full bg-white" />
                )}
              </button>
            </div>
          </>
        )}
        <canvas ref={canvasRef} className="hidden" />
      </div>

      {/* Thumbnails */}
      {capturedImages.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {capturedImages.map((img, i) => (
            <motion.div key={i} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="relative group">
              <img src={img} alt="" className="w-12 h-12 rounded-xl object-cover border border-[rgba(255,255,255,0.08)]" />
              <div className="absolute inset-0 rounded-xl bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                <CheckCircle2 size={16} className="text-[#34d399]" />
              </div>
            </motion.div>
          ))}
          <button onClick={() => { resetImages(); }} className="w-12 h-12 rounded-xl border border-[rgba(255,255,255,0.07)] bg-[rgba(255,255,255,0.03)] flex items-center justify-center text-[rgba(255,255,255,0.3)] hover:text-[#f87171] hover:border-[rgba(248,113,113,0.3)] transition-all">
            <RefreshCw size={13} />
          </button>
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={onBack} className="flex-1 py-3 rounded-xl text-sm font-medium text-[rgba(255,255,255,0.5)] border border-[rgba(255,255,255,0.07)] hover:text-white hover:bg-[rgba(255,255,255,0.04)] transition-all">
          Back
        </button>
        <button
          onClick={onNext}
          disabled={capturedImages.length < 1}
          className="flex-1 btn-accent py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Review {capturedImages.length} image{capturedImages.length !== 1 ? "s" : ""}
          <ChevronRight size={14} />
        </button>
      </div>
    </motion.div>
  );
}

/* ── Step 3 ── */
function StepReview({ meta, onSubmit, onBack, loading }: { meta: MetaForm; onSubmit: () => void; onBack: () => void; loading: boolean }) {
  const { capturedImages } = useEnrollmentStore();
  return (
    <motion.div key="review" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }} className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-white mb-1 tracking-tight">Review & enroll</h2>
        <p className="text-[13px] text-[rgba(255,255,255,0.38)]">Confirm before submitting.</p>
      </div>

      <div className="rounded-xl border border-[rgba(255,255,255,0.07)] bg-[rgba(255,255,255,0.025)] p-4 space-y-2.5">
        {[{ l: "Name", v: meta.name }, { l: "Email", v: meta.email }, ...(meta.phone ? [{ l: "Phone", v: meta.phone }] : [])].map(({ l, v }) => (
          <div key={l} className="flex items-center justify-between text-[13px]">
            <span className="text-[rgba(255,255,255,0.38)]">{l}</span>
            <span className="text-white font-medium">{v}</span>
          </div>
        ))}
      </div>

      <div>
        <p className="text-[12px] text-[rgba(255,255,255,0.35)] mb-3">{capturedImages.length} image{capturedImages.length !== 1 ? "s" : ""} ready</p>
        <div className="flex gap-2 flex-wrap">
          {capturedImages.map((img, i) => (
            <div key={i} className="relative">
              <img src={img} alt="" className="w-14 h-14 rounded-xl object-cover border border-[rgba(124,124,255,0.25)]" />
              <div className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-[#34d399] flex items-center justify-center">
                <CheckCircle2 size={10} className="text-black" />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-[rgba(255,255,255,0.07)] bg-[rgba(255,255,255,0.02)] p-4 flex gap-3">
        <div className="w-4 h-4 shrink-0 mt-0.5">
          <svg viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" stroke="rgba(165,180,252,0.5)" strokeWidth="1"/><path d="M8 5v4M8 11v.5" stroke="rgba(165,180,252,0.8)" strokeWidth="1.2" strokeLinecap="round"/></svg>
        </div>
        <p className="text-[11px] text-[rgba(255,255,255,0.35)] leading-relaxed">
          Images are processed locally to generate a 512-d embedding. Raw images are discarded — only the encrypted vector is stored.
        </p>
      </div>

      <div className="flex gap-3">
        <button onClick={onBack} disabled={loading} className="flex-1 py-3 rounded-xl text-sm font-medium text-[rgba(255,255,255,0.5)] border border-[rgba(255,255,255,0.07)] hover:text-white hover:bg-[rgba(255,255,255,0.04)] transition-all disabled:opacity-40">
          Back
        </button>
        <button onClick={onSubmit} disabled={loading} className="flex-1 btn-accent py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
          {loading ? <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>Enrolling…</> : <><Upload size={14} />Enroll Identity</>}
        </button>
      </div>
    </motion.div>
  );
}

/* ── Step 4 ── */
function StepSuccess({ result }: { result: EnrollmentResponse }) {
  return (
    <motion.div key="success" initial={{ opacity: 0, scale: 0.93 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }} className="text-center space-y-6 py-4">
      <div className="flex justify-center">
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.15, type: "spring", stiffness: 220, damping: 16 }}
          className="relative w-20 h-20 rounded-full bg-[rgba(52,211,153,0.12)] border border-[rgba(52,211,153,0.25)] flex items-center justify-center">
          <CheckCircle2 size={32} className="text-[#34d399]" />
          <div className="absolute inset-0 rounded-full bg-[rgba(52,211,153,0.15)] pulse-ring" />
        </motion.div>
      </div>

      <div>
        <h2 className="text-xl font-bold text-white mb-2 tracking-tight">Identity Enrolled</h2>
        <p className="text-[13px] text-[rgba(255,255,255,0.4)]">Biometric profile ready for authentication.</p>
      </div>

      <div className="rounded-xl border border-[rgba(52,211,153,0.15)] bg-[rgba(52,211,153,0.04)] p-4 text-left space-y-2.5 max-w-xs mx-auto">
        {[
          { l: "Status", v: "Enrolled", c: "#34d399" },
          { l: "Confidence", v: `${result.confidence.toFixed(1)}%`, c: "#a5b4fc" },
          { l: "Images", v: `${result.images_processed}`, c: "white" },
          { l: "User ID", v: result.user_id.slice(0, 8) + "…", c: "rgba(255,255,255,0.4)" },
        ].map(({ l, v, c }) => (
          <div key={l} className="flex items-center justify-between text-[13px]">
            <span className="text-[rgba(255,255,255,0.38)]">{l}</span>
            <span className="font-medium" style={{ color: c }}>{v}</span>
          </div>
        ))}
      </div>

      <div className="flex gap-3 justify-center">
        <a href="/verify"><button className="btn-primary px-5 py-2.5 rounded-xl text-sm font-medium text-white">Try Verification</button></a>
        <a href="/dashboard"><button className="btn-accent px-5 py-2.5 rounded-xl text-sm font-semibold text-white flex items-center gap-2"><Sparkles size={13} />Dashboard</button></a>
      </div>
    </motion.div>
  );
}

/* ── Main ── */
export default function EnrollPage() {
  const [meta, setMeta] = useState<MetaForm | null>(null);
  const { step, setStep, capturedImages, isProcessing, setProcessing, result, setResult, setError, reset } = useEnrollmentStore();

  const handleSubmit = async () => {
    if (!meta || !capturedImages.length) return;
    setProcessing(true);
    try {
      const form = new FormData();
      form.append("name", meta.name); form.append("email", meta.email);
      if (meta.phone) form.append("phone", meta.phone);
      for (const dataUrl of capturedImages) {
        const res = await fetch(dataUrl); const blob = await res.blob();
        form.append("images", blob, "face.jpg");
      }
      const { data } = await enrollmentApi.enroll(form);
      setResult(data); setStep(4);
    } catch (err: any) {
      const msg = extractErrorMsg(err, "Enrollment failed");
      setError(msg); toast.error(msg);
    } finally { setProcessing(false); }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4 py-12 relative overflow-hidden">
      <div className="absolute inset-0 hero-glow opacity-50 pointer-events-none" />
      <div className="absolute inset-0 dot-grid opacity-[0.25] pointer-events-none" />

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }} className="relative w-full max-w-[480px]">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/logo.png" alt="NeoFace Logo" width={200} height={60} className="h-10 w-auto object-contain" />
          </Link>
          {step < 4 && (
            <button onClick={reset} className="flex items-center gap-1.5 text-[12px] text-[rgba(255,255,255,0.28)] hover:text-[rgba(255,255,255,0.6)] transition-colors">
              <X size={13} /> Reset
            </button>
          )}
        </div>

        <StepDots current={step} />

        <div className="rounded-2xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.025)] p-8 min-h-[460px] flex flex-col justify-center">
          <AnimatePresence mode="wait">
            {step === 1 && <StepInfo key="1" onNext={(d) => { setMeta(d); setStep(2); }} />}
            {step === 2 && <StepCapture key="2" onNext={() => setStep(3)} onBack={() => setStep(1)} />}
            {step === 3 && meta && <StepReview key="3" meta={meta} onSubmit={handleSubmit} onBack={() => setStep(2)} loading={isProcessing} />}
            {step === 4 && result && <StepSuccess key="4" result={result} />}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
