"use client";
import { useRef, useState } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";

type Lang = "REST" | "Python" | "Node.js" | "Go" | "cURL";

const SNIPPETS: Record<Lang, { lines: { type: string; text: string }[] }> = {
  REST: {
    lines: [
      { type: "comment",  text: "# Authorize a biometric payment" },
      { type: "keyword",  text: "POST " },
      { type: "url",      text: "https://api.neoface.io/payments/authorize" },
      { type: "blank",    text: "" },
      { type: "key",      text: "Authorization: " },
      { type: "value",    text: "Bearer nf_live_sk_xxxxxxxxxxxx" },
      { type: "key",      text: "Content-Type: " },
      { type: "value",    text: "application/json" },
      { type: "blank",    text: "" },
      { type: "bracket",  text: "{" },
      { type: "field",    text: '  "faceId":     ' },
      { type: "string",   text: '"verified",' },
      { type: "field",    text: '  "irisId":     ' },
      { type: "string",   text: '"verified",' },
      { type: "field",    text: '  "fingerprint":' },
      { type: "string",   text: '"verified",' },
      { type: "field",    text: '  "amount":     ' },
      { type: "string",   text: '"1250",' },
      { type: "field",    text: '  "merchant":   ' },
      { type: "string",   text: '"merchant_reliance_01"' },
      { type: "bracket",  text: "}" },
      { type: "blank",    text: "" },
      { type: "comment",  text: "# → 200 OK" },
      { type: "bracket",  text: "{" },
      { type: "field",    text: '  "status":     ' },
      { type: "string",   text: '"approved",' },
      { type: "field",    text: '  "txnId":      ' },
      { type: "string",   text: '"txn_8f2k9a3b",' },
      { type: "field",    text: '  "amount":     ' },
      { type: "number",   text: "1250," },
      { type: "field",    text: '  "latency_ms": ' },
      { type: "number",   text: "87" },
      { type: "bracket",  text: "}" },
    ],
  },
  Python: {
    lines: [
      { type: "comment",   text: "# pip install neoface" },
      { type: "keyword",   text: "import " },
      { type: "value",     text: "neoface" },
      { type: "blank",     text: "" },
      { type: "keyword",   text: "client " },
      { type: "value",     text: "= neoface.Client(" },
      { type: "string",    text: '"nf_live_sk_xxxxxxxxxxxx"' },
      { type: "bracket",   text: ")" },
      { type: "blank",     text: "" },
      { type: "keyword",   text: "result " },
      { type: "value",     text: "= client.payments.authorize(" },
      { type: "field",     text: "    face_id=" },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "    iris_id=" },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "    fingerprint=" },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "    amount=" },
      { type: "number",    text: "1250," },
      { type: "bracket",   text: ")" },
      { type: "blank",     text: "" },
      { type: "keyword",   text: "if " },
      { type: "value",     text: 'result.status == "approved":' },
      { type: "function",  text: "    print" },
      { type: "bracket",   text: "(" },
      { type: "string",    text: 'f"✓ Payment {result.txn_id} authorized"' },
      { type: "bracket",   text: ")" },
    ],
  },
  "Node.js": {
    lines: [
      { type: "comment",   text: "// npm install @neoface/node" },
      { type: "keyword",   text: "import " },
      { type: "value",     text: "{ NeoFace } " },
      { type: "keyword",   text: "from " },
      { type: "string",    text: '"@neoface/node"' },
      { type: "blank",     text: "" },
      { type: "keyword",   text: "const " },
      { type: "value",     text: "client " },
      { type: "keyword",   text: "= new " },
      { type: "function",  text: "NeoFace" },
      { type: "bracket",   text: "({" },
      { type: "field",     text: "  apiKey: " },
      { type: "value",     text: "process.env." },
      { type: "string",    text: "NEOFACE_KEY" },
      { type: "bracket",   text: "})" },
      { type: "blank",     text: "" },
      { type: "keyword",   text: "const " },
      { type: "value",     text: "{ status, txnId } " },
      { type: "keyword",   text: "= await " },
      { type: "value",     text: "client.payments.authorize" },
      { type: "bracket",   text: "({" },
      { type: "field",     text: "  faceId: " },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "  irisId: " },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "  fingerprint: " },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "  amount: " },
      { type: "number",    text: "1250" },
      { type: "bracket",   text: "})" },
      { type: "blank",     text: "" },
      { type: "comment",   text: '// → { status: "approved", txnId: "txn_8f2k9a3b" }' },
    ],
  },
  Go: {
    lines: [
      { type: "comment",   text: "// go get github.com/neoface/go-sdk" },
      { type: "keyword",   text: "package " },
      { type: "value",     text: "main" },
      { type: "blank",     text: "" },
      { type: "keyword",   text: "import " },
      { type: "bracket",   text: "(" },
      { type: "string",    text: '  "github.com/neoface/go-sdk"' },
      { type: "bracket",   text: ")" },
      { type: "blank",     text: "" },
      { type: "value",     text: "client " },
      { type: "keyword",   text: ":= " },
      { type: "function",  text: "neoface.New" },
      { type: "bracket",   text: "(" },
      { type: "string",    text: '"nf_live_sk_xxxx"' },
      { type: "bracket",   text: ")" },
      { type: "blank",     text: "" },
      { type: "value",     text: "result, err " },
      { type: "keyword",   text: ":= " },
      { type: "value",     text: "client.Payments." },
      { type: "function",  text: "Authorize" },
      { type: "bracket",   text: "(&neoface.PaymentRequest{" },
      { type: "field",     text: "  FaceID:      " },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "  IrisID:      " },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "  Fingerprint: " },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: "  Amount:      " },
      { type: "number",    text: "1250," },
      { type: "bracket",   text: "})" },
    ],
  },
  cURL: {
    lines: [
      { type: "keyword",   text: "curl " },
      { type: "value",     text: "-X POST \\" },
      { type: "value",     text: "  https://api.neoface.io/payments/authorize \\" },
      { type: "field",     text: "  -H " },
      { type: "string",    text: '"Authorization: Bearer nf_live_sk_xxxx" \\' },
      { type: "field",     text: "  -H " },
      { type: "string",    text: '"Content-Type: application/json" \\' },
      { type: "field",     text: "  -d " },
      { type: "bracket",   text: "'" },
      { type: "bracket",   text: "  {" },
      { type: "field",     text: '    "faceId": ' },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: '    "irisId": ' },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: '    "fingerprint": ' },
      { type: "string",    text: '"verified",' },
      { type: "field",     text: '    "amount": ' },
      { type: "string",    text: '"1250"' },
      { type: "bracket",   text: "  }" },
      { type: "bracket",   text: "'" },
    ],
  },
};

const TYPE_COLOR: Record<string, string> = {
  comment:  "rgba(255,255,255,0.28)",
  keyword:  "#c792ea",
  string:   "#c3e88d",
  number:   "#f78c6c",
  function: "#82aaff",
  field:    "#89ddff",
  key:      "#89ddff",
  value:    "#eeffff",
  url:      "#00C2FF",
  bracket:  "rgba(255,255,255,0.55)",
  blank:    "transparent",
};

const FEATURES = [
  "Biometric payment APIs",
  "Merchant SDK integration",
  "Real-time webhooks",
  "POS & terminal support",
  "Banking & fintech ready",
  "99.99% uptime SLA",
];

function CodeWindow({ lang }: { lang: Lang }) {
  const snippet = SNIPPETS[lang];

  return (
    <div className="relative h-full flex flex-col bg-[#050505]/80 backdrop-blur-2xl group">
      <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent pointer-events-none opacity-50 group-hover:opacity-100 transition-opacity" />
      <div className="absolute inset-0 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.1)] rounded-2xl pointer-events-none" />
      {/* Chrome */}
      <div className="flex items-center px-4 py-3 border-b border-white/5 bg-white/[0.02]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-[#f87171]/80 shadow-[0_0_8px_rgba(248,113,113,0.4)]" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#fbbf24]/80 shadow-[0_0_8px_rgba(251,191,36,0.4)]" />
          <div className="w-2.5 h-2.5 rounded-full bg-[#00E5A8]/80 shadow-[0_0_8px_rgba(0,229,168,0.4)]" />
        </div>
        <div className="ml-4 flex-1" />
        <div
          className="text-[10px] font-semibold px-2.5 py-0.5 rounded border shadow-sm backdrop-blur-md"
          style={{
            borderColor: "rgba(0,229,168,0.3)",
            background: "rgba(0,229,168,0.08)",
            color: "#00E5A8",
          }}
        >
          {lang}
        </div>
      </div>

      {/* Code */}
      <div className="flex-1 overflow-auto p-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={lang}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.3 }}
          >
            {snippet.lines.map((line, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.025, duration: 0.2 }}
                className="flex items-start leading-[1.8] min-h-[1.8em]"
              >
                <span className="text-[rgba(255,255,255,0.12)] select-none w-7 text-right mr-4 text-[11px] shrink-0 pt-[1px]">
                  {line.type !== "blank" ? i + 1 : ""}
                </span>
                <span style={{ color: TYPE_COLOR[line.type] ?? "#eeffff", fontFamily: "var(--font-geist-mono), monospace", fontSize: 12 }}>
                  {line.text}
                </span>
              </motion.div>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

export function DeveloperSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-60px" });
  const [activeLang, setActiveLang] = useState<Lang>("REST");

  const LANGS: Lang[] = ["REST", "Python", "Node.js", "Go", "cURL"];

  return (
    <section id="developers" ref={ref} className="relative section-pad px-6">
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: "radial-gradient(ellipse 60% 50% at 70% 50%, rgba(130,170,255,0.04) 0%, transparent 65%)" }}
      />
      {/* ── Subtle Dot Grid Pattern ── */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-100"
        style={{
          backgroundImage: `radial-gradient(circle at center, rgba(255,255,255,0.15) 1.5px, transparent 1.5px)`,
          backgroundSize: '32px 32px',
          maskImage: 'linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 15%, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)',
          WebkitMaskImage: 'linear-gradient(to bottom, rgba(0,0,0,0) 0%, rgba(0,0,0,1) 15%, rgba(0,0,0,1) 85%, rgba(0,0,0,0) 100%)'
        }}
      />

      <div className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-[1fr_1.4fr] gap-16 items-start">
          {/* Left text */}
          <motion.div
            initial={{ opacity: 0, x: -28 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="lg:sticky lg:top-32"
          >
            <div className="tag tag-accent inline-flex mb-6">Developer platform</div>
            <h2 className="text-title-1 text-white mb-6 leading-tight">
              From API To Payment.<br />
              <span className="text-gradient-accent">In Minutes.</span>
            </h2>
            <p className="text-[18px] text-[rgba(255,255,255,0.42)] leading-[1.7] mb-12 max-w-sm">
              Integrate biometric payments into apps, banks, retailers, POS systems, and fintech platforms with a developer-first API.
            </p>

            {/* Features list */}
            <ul className="space-y-3">
              {FEATURES.map((f, i) => (
                <motion.li
                  key={f}
                  initial={{ opacity: 0, x: -16 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ delay: 0.1 + i * 0.07, duration: 0.5 }}
                  className="flex items-center gap-3 text-[14px] text-[rgba(255,255,255,0.55)]"
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <circle cx="7" cy="7" r="6.5" stroke="rgba(0,229,168,0.4)"/>
                    <path d="M4.5 7 L6.2 8.7 L9.5 5.4" stroke="#00E5A8" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                  {f}
                </motion.li>
              ))}
            </ul>

            {/* Protocol badge */}
            <div className="mt-10 inline-flex items-center gap-3 bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.07)] rounded-xl px-4 py-3">
              <div className="text-[#00C2FF] font-mono text-[12px] font-semibold">REST</div>
              <div className="w-px h-4 bg-[rgba(255,255,255,0.1)]" />
              <div className="text-[#00C2FF] font-mono text-[12px] font-semibold">GraphQL</div>
              <div className="w-px h-4 bg-[rgba(255,255,255,0.1)]" />
              <div className="text-[#00E5A8] font-mono text-[12px] font-semibold">Webhooks</div>
            </div>
          </motion.div>

          {/* Right — code window */}
          <motion.div
            initial={{ opacity: 0, x: 28 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col gap-4"
          >
            {/* Language tabs */}
            <div className="flex gap-1 flex-wrap">
              {LANGS.map(lang => (
                <button
                  key={lang}
                  onClick={() => setActiveLang(lang)}
                  className={`px-3.5 py-1.5 text-[12px] font-medium rounded-lg transition-all duration-200 ${
                    activeLang === lang
                      ? "bg-[rgba(0,229,168,0.15)] border border-[rgba(0,229,168,0.3)] text-[#00E5A8]"
                      : "text-[rgba(255,255,255,0.35)] hover:text-white hover:bg-[rgba(255,255,255,0.04)] border border-transparent"
                  }`}
                >
                  {lang}
                </button>
              ))}
            </div>

            {/* Code window */}
            <div className="h-[500px] rounded-2xl overflow-hidden shadow-[0_32px_64px_-16px_rgba(0,0,0,0.8)] relative">
              <div className="absolute inset-0 bg-gradient-to-tr from-[#00E5A8]/10 via-transparent to-[#0EA5E9]/10 opacity-30 pointer-events-none" />
              <CodeWindow lang={activeLang} />
            </div>

            {/* Payment API stats row */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Avg Latency", val: "87ms", color: "#00E5A8" },
                { label: "p99 Latency", val: "140ms", color: "#00C2FF" },
                { label: "Uptime SLA",  val: "99.99%", color: "#00E5A8" },
              ].map(s => (
                <div key={s.label} className="bg-[rgba(255,255,255,0.025)] border border-[rgba(255,255,255,0.06)] rounded-xl p-3 text-center">
                  <div className="font-mono font-bold text-lg" style={{ color: s.color }}>{s.val}</div>
                  <div className="text-[10px] text-[rgba(255,255,255,0.3)] mt-1">{s.label}</div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
