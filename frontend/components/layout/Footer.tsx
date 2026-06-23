import Link from "next/link";
import Image from "next/image";

const COLS = {
  Products: ["Face Auth", "Iris Auth", "Fingerprint Auth", "Risk Scoring"],
  Developers: ["Documentation", "API Reference", "SDKs", "Status"],
  Company: ["About", "Blog", "Careers", "Press"],
  Legal: ["Privacy Policy", "Terms of Service", "Compliance", "Cookies"],
};

export function Footer() {
  return (
    <footer className="border-t border-[rgba(255,255,255,0.055)] py-16 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-14">
          {/* Brand */}
          <div className="col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-5 group">
              <Image src="/NeoFaceLogoFinal.png" alt="NeoFace Logo" width={200} height={60} className="h-12 w-auto object-contain" />
            </Link>
            <p className="text-[13px] text-[rgba(255,255,255,0.3)] leading-[1.6] max-w-[200px]">
              Biometric Authentication Infrastructure for the next generation of apps.
            </p>
          </div>

          {/* Links */}
          {Object.entries(COLS).map(([title, items]) => (
            <div key={title}>
              <h4 className="text-[10px] font-semibold text-[rgba(255,255,255,0.22)] uppercase tracking-[0.15em] mb-4">
                {title}
              </h4>
              <ul className="space-y-2.5">
                {items.map((item) => (
                  <li key={item}>
                    <Link
                      href="#"
                      className="text-[13px] text-[rgba(255,255,255,0.38)] hover:text-white transition-colors duration-150"
                    >
                      {item}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="separator mb-6" />
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-[12px] text-[rgba(255,255,255,0.22)]">
            © 2026 NeoFace, All rights reserved.
          </p>
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-1.5 text-[11px] text-[rgba(255,255,255,0.22)]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#34d399] animate-pulse" />
              Auth API: Operational
            </div>
            <span className="text-[11px] text-[rgba(255,255,255,0.18)] font-mono">v1.0.0</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
