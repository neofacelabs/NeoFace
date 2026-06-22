"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Scan, ShieldCheck, ShieldAlert, AlertCircle, CheckCircle2, XCircle,
  Camera, RefreshCw, Eye, Activity, User, Brain, Zap,
  CreditCard, DollarSign, Loader2, Upload,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { verificationApi, livenessApi, deepfakeApi, riskApi, webrtcApi, usersApi, paymentsApi } from "@/lib/api";
import { useVerificationStore } from "@/store/verification";
import { cn } from "@/lib/utils";
import type { VerificationResponse, PassiveLivenessResult, DeepfakeResult, RiskScoreResult } from "@/types";

// ── Liveness check pill ───────────────────────────────────────────────────────
function LivenessCheck({ label, passed }: { label: string; passed: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {passed
        ? <CheckCircle2 className="w-4 h-4 text-success shrink-0" />
        : <div className="w-4 h-4 rounded-full border border-border-DEFAULT shrink-0" />}
      <span className={passed ? "text-white" : "text-text-muted"}>{label}</span>
    </div>
  );
}

// ── Trust Engine mini badge ───────────────────────────────────────────────────
function TrustBadge({ label, value, color, icon: Icon }: {
  label: string; value: string; color: string; icon: any;
}) {
  return (
    <div className="flex items-center justify-between text-xs py-1.5 px-3 rounded-xl"
      style={{ background: `${color}08`, border: `1px solid ${color}20` }}>
      <div className="flex items-center gap-1.5">
        <Icon size={10} style={{ color }} />
        <span className="text-[rgba(255,255,255,0.4)]">{label}</span>
      </div>
      <span className="font-semibold" style={{ color }}>{value}</span>
    </div>
  );
}

// ── NeoFace Trust Score badge ─────────────────────────────────────────────────
function TrustScoreBlock({ risk }: { risk: RiskScoreResult }) {
  const color = risk.decision === "approve" ? "#00E5A8"
    : risk.decision === "step_up" ? "#f59e0b"
    : "#f87171";
  const Icon = risk.decision === "approve" ? ShieldCheck
    : risk.decision === "step_up" ? ShieldAlert
    : XCircle;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="rounded-2xl p-4 border"
      style={{ background: `${color}08`, borderColor: `${color}25` }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: `${color}15`, border: `1px solid ${color}25` }}>
            <Icon size={13} style={{ color }} />
          </div>
          <span className="text-xs font-semibold text-white">NeoFace Trust Score</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-2xl font-bold" style={{ color }}>{risk.final_trust_score.toFixed(0)}</span>
          <span className="text-[9px] font-bold tracking-widest uppercase" style={{ color }}>
            {risk.decision.replace("_", "-")}
          </span>
        </div>
      </div>
      {/* Score bar */}
      <div className="h-1.5 rounded-full bg-[rgba(255,255,255,0.06)] overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: `linear-gradient(90deg, ${color}80, ${color})` }}
          initial={{ width: 0 }}
          animate={{ width: `${risk.final_trust_score}%` }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
      <p className="text-[10px] text-[rgba(255,255,255,0.25)] mt-2 leading-relaxed">{risk.explanation}</p>
    </motion.div>
  );
}

// ── Result view ───────────────────────────────────────────────────────────────
function VerificationResult({
  result, passiveLiveness, deepfake, risk, capturedBlob, onReset,
}: {
  result: VerificationResponse;
  passiveLiveness: PassiveLivenessResult | null;
  deepfake: DeepfakeResult | null;
  risk: RiskScoreResult | null;
  capturedBlob: Blob | null;
  onReset: () => void;
}) {
  const success = result.authenticated;
  const [userInfo, setUserInfo] = useState<any>(null);
  const [loadingUser, setLoadingUser] = useState(false);

  const [payAmount, setPayAmount] = useState("25.00");
  const [payDescription, setPayDescription] = useState("Biometric Pay Terminal Charge");
  const [paymentStatus, setPaymentStatus] = useState<"idle" | "processing" | "success" | "failed">("idle");
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [paymentTxId, setPaymentTxId] = useState<string | null>(null);

  useEffect(() => {
    if (success && result.user_id) {
      setLoadingUser(true);
      usersApi.get(result.user_id)
        .then(r => setUserInfo(r.data))
        .catch(err => console.error("Failed to load user info:", err))
        .finally(() => setLoadingUser(false));
    }
  }, [success, result.user_id]);

  const handleCharge = async () => {
    if (!capturedBlob) {
      toast.error("No captured image available for authorization");
      return;
    }
    setPaymentStatus("processing");
    setPaymentError(null);

    try {
      const formData = new FormData();
      formData.append("amount", parseFloat(payAmount).toString());
      formData.append("description", payDescription);
      formData.append("face_image", capturedBlob, "face.jpg");

      const response = await paymentsApi.authorize(formData);
      if (response.data.authorized) {
        setPaymentStatus("success");
        setPaymentTxId(response.data.transaction_id);
        toast.success("Payment authorized successfully!");
      } else {
        setPaymentStatus("failed");
        setPaymentError(response.data.failure_reason || "Payment authorization failed");
        toast.error("Payment authorization failed");
      }
    } catch (err: any) {
      console.error(err);
      const errMsg = err.response?.data?.detail || "Network error or server error";
      setPaymentStatus("failed");
      setPaymentError(errMsg);
      toast.error(errMsg);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-5 py-2"
    >
      {/* Status icon */}
      <div className="flex justify-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.1, type: "spring", stiffness: 200, damping: 15 }}
          className={cn(
            "relative w-20 h-20 rounded-full flex items-center justify-center",
            success ? "bg-success/15 border border-success/30" : "bg-error/15 border border-error/30"
          )}
        >
          {success
            ? <ShieldCheck className="w-10 h-10 text-success" />
            : <XCircle className="w-10 h-10 text-error" />}
          <motion.div
            animate={{ scale: [1, 1.6], opacity: [0.4, 0] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className={cn("absolute inset-0 rounded-full", success ? "bg-success/20" : "bg-error/20")}
          />
        </motion.div>
      </div>

      {/* Title */}
      <div className="text-center">
        <h2 className={cn("text-xl font-bold mb-1", success ? "text-success" : "text-error")}>
          {success ? "Identity Verified" : "Verification Failed"}
        </h2>
        {success ? (
          <p className="text-text-muted text-sm">
            Welcome back, <span className="text-white font-medium">{result.user_name ?? "User"}</span>
          </p>
        ) : (
          <p className="text-text-muted text-sm">{result.failure_reason ?? "Could not verify identity"}</p>
        )}
      </div>

      {/* Core biometric scores */}
      <div className="rounded-2xl p-4 border border-border-DEFAULT bg-white/[0.025] text-left space-y-2.5">
        <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Biometric Signals</p>
        {[
          { label: "Confidence", value: `${result.confidence_score.toFixed(1)}%`, ok: result.confidence_score > 80 },
          { label: "Liveness Score", value: `${result.liveness_score.toFixed(1)}`, ok: result.liveness_detail.is_live },
          { label: "Anti-Spoof", value: `${result.liveness_detail.anti_spoof_score.toFixed(1)}`, ok: result.liveness_detail.anti_spoof_score > 70 },
          { label: "Method", value: result.liveness_detail.method, ok: true },
        ].map(({ label, value, ok }) => (
          <div key={label} className="flex items-center justify-between text-sm">
            <span className="text-text-muted">{label}</span>
            <span className={cn("font-medium", ok ? "text-white" : "text-error")}>{value}</span>
          </div>
        ))}
      </div>

      {/* Liveness checks */}
      <div className="grid grid-cols-3 gap-2">
        <LivenessCheck label="Blink" passed={result.liveness_detail.blink_detected} />
        <LivenessCheck label="Head turn" passed={result.liveness_detail.head_turn_detected} />
        <LivenessCheck label="Expression" passed={result.liveness_detail.smile_detected} />
      </div>

      {/* Trust Engine results */}
      {(passiveLiveness || deepfake) && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Trust Engine</p>
          {passiveLiveness && (
            <TrustBadge
              label="Passive Liveness"
              value={passiveLiveness.is_live
                ? `LIVE · ${passiveLiveness.confidence.toFixed(0)}%`
                : `SPOOF · ${passiveLiveness.attack_type}`}
              color={passiveLiveness.is_live ? "#00E5A8" : "#f87171"}
              icon={Eye}
            />
          )}
          {deepfake && (
            <TrustBadge
              label="Deepfake Check"
              value={deepfake.is_deepfake
                ? `DETECTED · ${deepfake.attack_category}`
                : `Clean · ${(deepfake.deepfake_probability * 100).toFixed(1)}%`}
              color={deepfake.is_deepfake ? "#f87171" : "#00E5A8"}
              icon={Brain}
            />
          )}
        </div>
      )}

      {/* Matched Profile Details */}
      {success && (
        <div className="rounded-2xl p-4 border border-border-DEFAULT bg-white/[0.025] text-left space-y-3">
          <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">Matched Identity Profile</p>
          {loadingUser ? (
            <div className="space-y-2 animate-pulse">
              <div className="h-4 bg-white/5 rounded w-3/4" />
              <div className="h-4 bg-white/5 rounded w-1/2" />
              <div className="h-4 bg-white/5 rounded w-2/3" />
            </div>
          ) : userInfo ? (
            <div className="space-y-2 text-sm text-[rgba(255,255,255,0.7)]">
              <div className="flex items-center gap-2">
                <span className="text-text-muted text-xs w-20 shrink-0">Name:</span>
                <span className="text-white font-medium">{userInfo.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-text-muted text-xs w-20 shrink-0">Email:</span>
                <span className="text-white font-medium">{userInfo.email}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-text-muted text-xs w-20 shrink-0">Phone:</span>
                <span className="text-white font-medium">{userInfo.phone || "None linked"}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-text-muted text-xs w-20 shrink-0">Role:</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                  style={{
                    background: userInfo.role === "admin" ? "rgba(245,158,11,0.12)" : "rgba(124,124,255,0.12)",
                    color: userInfo.role === "admin" ? "#f59e0b" : "#818cf8",
                    border: `1px solid ${userInfo.role === "admin" ? "rgba(245,158,11,0.25)" : "rgba(124,124,255,0.25)"}`
                  }}>
                  {userInfo.role}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-text-muted text-xs w-20 shrink-0">Status:</span>
                <span className="flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${userInfo.is_active ? "bg-[#34d399]" : "bg-error"}`} />
                  {userInfo.is_active ? "Active" : "Suspended"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-text-muted text-xs w-20 shrink-0">Enrolled:</span>
                <span className="text-white font-medium">{new Date(userInfo.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-text-muted">Could not retrieve detailed profile metadata.</p>
          )}
        </div>
      )}

      {/* Charge Customer Form */}
      {success && userInfo && (
        <div className="rounded-2xl p-4 border border-border-DEFAULT bg-white/[0.025] text-left space-y-3">
          <div className="flex items-center gap-2 border-b border-white/5 pb-2">
            <CreditCard className="w-4 h-4 text-accent-soft" />
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider">Biometric Pay Terminal</h3>
          </div>

          {paymentStatus === "idle" && (
            <div className="space-y-3 pt-1">
              <div className="space-y-1.5">
                <label className="text-[10px] text-text-muted uppercase tracking-wider">Amount (USD)</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <DollarSign className="w-3.5 h-3.5 text-accent-soft" />
                  </div>
                  <input
                    type="number"
                    value={payAmount}
                    onChange={(e) => setPayAmount(e.target.value)}
                    className="w-full bg-black/30 border border-white/10 rounded-xl py-2 pl-8 pr-3 text-white font-medium text-xs focus:outline-none focus:border-accent-soft/50 transition-colors"
                    placeholder="25.00"
                    step="0.01"
                    min="0.01"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-[10px] text-text-muted uppercase tracking-wider">Description</label>
                <input
                  type="text"
                  value={payDescription}
                  onChange={(e) => setPayDescription(e.target.value)}
                  className="w-full bg-black/30 border border-white/10 rounded-xl py-2 px-3 text-white text-xs focus:outline-none focus:border-accent-soft/50 transition-colors"
                  placeholder="Terminal payment"
                />
              </div>

              <Button
                onClick={handleCharge}
                className="w-full bg-accent-violet/20 hover:bg-accent-violet/30 border border-accent-violet/30 text-white font-semibold py-2.5 rounded-xl transition-all flex items-center justify-center gap-2 text-xs"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-accent-soft" />
                Pay Now
              </Button>
            </div>
          )}

          {paymentStatus === "processing" && (
            <div className="py-4 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-accent-soft animate-spin" />
              <div className="text-center">
                <p className="text-xs font-semibold text-white">Settling Biometric Transaction</p>
                <p className="text-[10px] text-text-muted">Processing via mock Stripe ACH...</p>
              </div>
            </div>
          )}

          {paymentStatus === "success" && (
            <div className="space-y-3 pt-1">
              <div className="flex items-center gap-2 bg-success/10 border border-success/20 p-3 rounded-xl">
                <CheckCircle2 className="w-5 h-5 text-success shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-white">Transaction Approved</p>
                  <p className="text-[10px] text-text-muted">Charged ${payAmount} successfully.</p>
                </div>
              </div>
              {paymentTxId && (
                <div className="rounded-xl bg-black/30 p-2.5 border border-white/5 space-y-1 text-[10px]">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-text-muted">Transaction ID:</span>
                    <span className="font-mono text-white select-all">{paymentTxId}</span>
                  </div>
                  <div className="flex justify-between text-[10px]">
                    <span className="text-text-muted">Settlement:</span>
                    <span className="text-success font-medium">Stripe ACH Success</span>
                  </div>
                </div>
              )}
              <Button
                variant="outline"
                className="w-full text-white border-white/10 text-xs py-1.5 h-8"
                onClick={() => {
                  setPaymentStatus("idle");
                  setPaymentTxId(null);
                }}
              >
                New Charge
              </Button>
            </div>
          )}

          {paymentStatus === "failed" && (
            <div className="space-y-3 pt-1">
              <div className="flex items-center gap-2 bg-error/10 border border-error/20 p-3 rounded-xl">
                <XCircle className="w-5 h-5 text-error shrink-0" />
                <div>
                  <p className="text-xs font-semibold text-white">Payment Declined</p>
                  <p className="text-[10px] text-error">{paymentError || "Authorization failed"}</p>
                </div>
              </div>
              <Button
                className="w-full bg-white/5 hover:bg-white/10 text-white text-xs py-1.5 h-8"
                onClick={() => setPaymentStatus("idle")}
              >
                Try Again
              </Button>
            </div>
          )}
        </div>
      )}

      {/* NeoFace Trust Score */}
      {risk && <TrustScoreBlock risk={risk} />}

      <Button size="lg" onClick={onReset} variant="outline" className="w-full gap-2">
        <RefreshCw className="w-4 h-4" />
        Try Again
      </Button>
    </motion.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function VerifyPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const [cameraError, setCameraError] = useState<string>();

  const { isVerifying, result, setVerifying, setResult, setError, reset } = useVerificationStore();

  const [passiveLiveness, setPassiveLiveness] = useState<PassiveLivenessResult | null>(null);
  const [deepfakeResult, setDeepfakeResult] = useState<DeepfakeResult | null>(null);
  const [riskResult, setRiskResult] = useState<RiskScoreResult | null>(null);
  const [capturedBlob, setCapturedBlob] = useState<Blob | null>(null);

  // WebRTC States
  const [webrtcConnected, setWebrtcConnected] = useState(false);
  const [pcState, setPcState] = useState<RTCPeerConnection | null>(null);

  // ── Camera ────────────────────────────────────────────────────────────────
  const startCamera = useCallback(async () => {
    setCameraError(undefined);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.onloadedmetadata = () => {
          videoRef.current?.play();
          setCameraReady(true);
        };
      }
    } catch {
      setCameraError("Camera access denied. Enable camera permissions and refresh.");
    }
  }, []);

  const stopWebRTC = useCallback(() => {
    if (pcState) {
      pcState.close();
      setPcState(null);
    }
    setWebrtcConnected(false);
  }, [pcState]);

  const startWebRTC = async () => {
    if (!videoRef.current || !videoRef.current.srcObject) {
      toast.error("Camera is not active");
      return;
    }

    try {
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
      });

      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach(track => pc.addTrack(track, stream));

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const response = await webrtcApi.offer({
        sdp: pc.localDescription!.sdp,
        type: pc.localDescription!.type,
      });

      const answer = new RTCSessionDescription({
        sdp: response.data.sdp,
        type: response.data.type,
      });
      await pc.setRemoteDescription(answer);

      setPcState(pc);
      setWebrtcConnected(true);
      toast.success("WebRTC stream established");
    } catch (err) {
      console.error("WebRTC stream establishment failed:", err);
      toast.error("WebRTC stream failed. Using fallback HTTP polling.");
    }
  };

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    setCameraReady(false);
    stopWebRTC();
  }, [stopWebRTC]);

  useEffect(() => { startCamera(); return stopCamera; }, [startCamera, stopCamera]);

  // ── Verify ────────────────────────────────────────────────────────────────
  const handleVerify = async () => {
    if (!videoRef.current || !canvasRef.current || !cameraReady) return;
    setVerifying(true);
    setPassiveLiveness(null);
    setDeepfakeResult(null);
    setRiskResult(null);

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);

    canvas.toBlob(async (blob) => {
      if (!blob) { setError("Failed to capture frame"); return; }
      setCapturedBlob(blob);

      const makeForm = () => {
        const f = new FormData();
        f.append("image", blob, "verify.jpg");
        return f;
      };

      // Run face verify + passive liveness + deepfake in parallel
      const [verifyRes, livenessRes, deepfakeRes] = await Promise.allSettled([
        verificationApi.verify(makeForm()),
        livenessApi.check(makeForm()),
        deepfakeApi.check(makeForm()),
      ]);

      let verifyData: VerificationResponse | null = null;
      let livData: PassiveLivenessResult | null = null;
      let dfData: DeepfakeResult | null = null;

      if (verifyRes.status === "fulfilled") {
        verifyData = verifyRes.value.data;
        if (verifyData) {
          setResult(verifyData);
        }
      } else {
        const msg = (verifyRes.reason as any)?.response?.data?.detail || "Verification failed";
        setError(msg);
        toast.error(msg);
      }

      if (livenessRes.status === "fulfilled") {
        livData = livenessRes.value.data as PassiveLivenessResult;
        setPassiveLiveness(livData);
        if (!livData.is_live) toast.warning(`Spoof attempt detected: ${livData.attack_type}`);
      }

      if (deepfakeRes.status === "fulfilled") {
        dfData = deepfakeRes.value.data as DeepfakeResult;
        setDeepfakeResult(dfData);
        if (dfData.is_deepfake) toast.error(`⚠️ Deepfake detected: ${dfData.attack_category}`);
      }

      // Compute NeoFace Trust Score from gathered signals
      if (verifyData || livData || dfData) {
        try {
          const { data: riskData } = await riskApi.computeScore({
            face_score: verifyData ? verifyData.confidence_score : undefined,
            liveness_score: livData ? livData.confidence : undefined,
            deepfake_score: dfData ? (1 - dfData.deepfake_probability) * 100 : undefined,
          });
          setRiskResult(riskData as RiskScoreResult);
        } catch {
          // non-fatal — trust score is supplementary
        }
      }
    }, "image/jpeg", 0.92);
  };

  const handleUploadVerify = async (file: File) => {
    setVerifying(true);
    setPassiveLiveness(null);
    setDeepfakeResult(null);
    setRiskResult(null);
    setCapturedBlob(file);

    const makeForm = () => {
      const f = new FormData();
      f.append("image", file, file.name);
      return f;
    };

    try {
      const [verifyRes, livenessRes, deepfakeRes] = await Promise.allSettled([
        verificationApi.verify(makeForm()),
        livenessApi.check(makeForm()),
        deepfakeApi.check(makeForm()),
      ]);

      let verifyData: VerificationResponse | null = null;
      let livData: PassiveLivenessResult | null = null;
      let dfData: DeepfakeResult | null = null;

      if (verifyRes.status === "fulfilled") {
        verifyData = verifyRes.value.data;
        if (verifyData) {
          setResult(verifyData);
        }
      } else {
        const msg = (verifyRes.reason as any)?.response?.data?.detail || "Verification failed";
        setError(msg);
        toast.error(msg);
      }

      if (livenessRes.status === "fulfilled") {
        livData = livenessRes.value.data as PassiveLivenessResult;
        setPassiveLiveness(livData);
        if (!livData.is_live) toast.warning(`Spoof attempt detected: ${livData.attack_type}`);
      }

      if (deepfakeRes.status === "fulfilled") {
        dfData = deepfakeRes.value.data as DeepfakeResult;
        setDeepfakeResult(dfData);
        if (dfData.is_deepfake) toast.error(`⚠️ Deepfake detected: ${dfData.attack_category}`);
      }

      if (verifyData || livData || dfData) {
        try {
          const { data: riskData } = await riskApi.computeScore({
            face_score: verifyData ? verifyData.confidence_score : undefined,
            liveness_score: livData ? livData.confidence : undefined,
            deepfake_score: dfData ? (1 - dfData.deepfake_probability) * 100 : undefined,
          });
          setRiskResult(riskData as RiskScoreResult);
        } catch {
          // non-fatal
        }
      }
    } catch (err: any) {
      console.error(err);
      toast.error("An error occurred during verification");
    } finally {
      setVerifying(false);
    }
  };

  const handleReset = () => {
    reset();
    setPassiveLiveness(null);
    setDeepfakeResult(null);
    setRiskResult(null);
    setCapturedBlob(null);
    startCamera();
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4 py-12">
      <div className="absolute inset-0 bg-grid opacity-40 pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-glow-purple opacity-30 pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative w-full max-w-lg"
      >
        {/* Logo bar */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div className="w-9 h-9 rounded-xl bg-accent-violet/20 border border-accent-violet/30 flex items-center justify-center">
            <Scan className="w-4 h-4 text-accent-soft" />
          </div>
          <span className="font-bold text-lg text-white">
            NeoFace <span className="text-accent-soft">Verify</span>
          </span>
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-semibold ml-1"
            style={{ background: "rgba(99,102,241,0.12)", border: "1px solid rgba(99,102,241,0.25)", color: "#818cf8" }}>
            <Zap size={8} />
            TRUST ENGINE
          </div>
        </div>

        <div className="glass-strong rounded-3xl border border-border-strong p-8">
          <AnimatePresence mode="wait">
            {result ? (
              <VerificationResult
                key="result"
                result={result}
                passiveLiveness={passiveLiveness}
                deepfake={deepfakeResult}
                risk={riskResult}
                capturedBlob={capturedBlob}
                onReset={handleReset}
              />
            ) : (
              <motion.div key="camera" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
                <div className="text-center">
                  <h1 className="text-xl font-bold text-white mb-1">Face Verification</h1>
                  <p className="text-sm text-text-muted">
                    Position your face · runs liveness + deepfake + trust score
                  </p>
                </div>

                {/* Camera viewport */}
                <div className="relative rounded-2xl overflow-hidden bg-black/40 border border-border-DEFAULT aspect-[4/3]">
                  {cameraError ? (
                    <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 p-6">
                      <AlertCircle className="w-12 h-12 text-error/70" />
                      <p className="text-sm text-text-muted text-center">{cameraError}</p>
                      <Button variant="outline" onClick={startCamera}>Retry</Button>
                    </div>
                  ) : (
                    <>
                      <video ref={videoRef} className="w-full h-full object-cover" muted playsInline />

                      {/* Face oval + corners */}
                      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <div className="relative w-48 h-60">
                          <motion.div
                            animate={{
                              borderColor: isVerifying
                                ? ["rgba(99,102,241,0.8)", "rgba(34,197,94,0.8)", "rgba(99,102,241,0.8)"]
                                : "rgba(99,102,241,0.5)"
                            }}
                            transition={{ duration: 1.5, repeat: isVerifying ? Infinity : 0 }}
                            className="absolute inset-0 rounded-full border-2"
                          />
                          {["top-0 left-0 border-t-2 border-l-2", "top-0 right-0 border-t-2 border-r-2",
                            "bottom-0 left-0 border-b-2 border-l-2", "bottom-0 right-0 border-b-2 border-r-2",
                          ].map((cls, i) => (
                            <motion.div key={i}
                              className={`absolute w-5 h-5 ${cls} border-accent-soft`}
                              animate={{ opacity: isVerifying ? [1, 0.3, 1] : 1 }}
                              transition={{ duration: 0.8, repeat: isVerifying ? Infinity : 0, delay: i * 0.1 }}
                            />
                          ))}
                          {isVerifying && (
                            <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-accent-violet to-transparent scan-line" />
                          )}
                        </div>
                      </div>

                      {/* Scanning module tags */}
                      {isVerifying && (
                        <div className="absolute top-3 left-3 flex flex-col gap-1.5">
                          {[
                            { label: "Face ID", color: "#818cf8" },
                            { label: "Liveness", color: "#00E5A8" },
                            { label: "Deepfake", color: "#f87171" },
                          ].map(({ label, color }, i) => (
                            <motion.div key={label}
                              initial={{ opacity: 0, x: -8 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: i * 0.12 }}
                              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[9.5px]"
                              style={{ background: "rgba(0,0,0,0.75)", color, border: `1px solid ${color}30` }}>
                              <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: color }} />
                              {label}
                            </motion.div>
                          ))}
                        </div>
                      )}

                      {/* Camera status */}
                      <div className="absolute top-3 right-3">
                        {isVerifying ? (
                          <div className="flex items-center gap-1.5 glass rounded-full px-2.5 py-1.5 text-xs text-accent-soft">
                            <Activity className="w-3 h-3 animate-pulse" />
                            Scanning…
                          </div>
                        ) : cameraReady ? (
                          <div className="flex items-center gap-1.5 glass rounded-full px-2.5 py-1.5 text-xs text-success">
                            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                            LIVE
                          </div>
                        ) : null}
                      </div>
                    </>
                  )}
                  <canvas ref={canvasRef} className="hidden" />
                </div>

                {/* Hints */}
                <div className="grid grid-cols-3 gap-3 text-center">
                  {[
                    { icon: User, text: "Look directly at camera" },
                    { icon: Eye, text: "Blink naturally" },
                    { icon: Activity, text: "Slight head movement" },
                  ].map(({ icon: Icon, text }) => (
                    <div key={text} className="glass rounded-xl p-3 border border-border-DEFAULT">
                      <Icon className="w-4 h-4 text-accent-soft mx-auto mb-1.5" />
                      <p className="text-xs text-text-muted leading-tight">{text}</p>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2">
                  <Button
                    size="xl"
                    className="flex-1 gap-2"
                    onClick={handleVerify}
                    loading={isVerifying}
                    disabled={!cameraReady || isVerifying || webrtcConnected}
                  >
                    {isVerifying ? "Scanning…" : (
                      <><ShieldCheck className="w-4 h-4" />Verify Identity</>
                    )}
                  </Button>
                  <Button
                    size="xl"
                    variant={webrtcConnected ? "danger" : "outline"}
                    className="flex-1 gap-2 text-white"
                    onClick={webrtcConnected ? stopWebRTC : startWebRTC}
                    disabled={!cameraReady || isVerifying}
                  >
                    <Activity className={cn("w-4 h-4", webrtcConnected && "animate-pulse")} />
                    {webrtcConnected ? "Stop WebRTC" : "WebRTC Stream"}
                  </Button>
                </div>

                <input
                  type="file"
                  id="photo-upload"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUploadVerify(file);
                  }}
                />
                <Button
                  size="xl"
                  variant="outline"
                  className="w-full gap-2 border-dashed border-white/20 text-white mt-2"
                  onClick={() => document.getElementById("photo-upload")?.click()}
                  disabled={isVerifying}
                >
                  <Upload className="w-4 h-4 text-accent-soft" />
                  Upload Photo Fallback
                </Button>

                <p className="text-center text-xs text-text-subtle">
                  Not enrolled?{" "}
                  <a href="/enroll" className="text-accent-soft hover:text-white transition-colors">
                    Enroll first →
                  </a>
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
