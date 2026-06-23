import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Toaster } from "sonner";
import "./globals.css";
import { Providers } from "./providers";
import { SmoothScroll } from "@/components/core/SmoothScroll";
import { NoiseOverlay } from "@/components/core/NoiseOverlay";

export const metadata: Metadata = {
  title: {
    default: "NeoFace Labs — Biometric Authentication as a Service",
    template: "%s | NeoFace Labs",
  },
  description:
    "Building the infrastructure where face, fingerprint, and iris intelligence power authentication, trust, and digital identity.",
  keywords: [
    "biometric identity",
    "face recognition",
    "identity infrastructure",
    "liveness detection",
    "authentication API",
    "iris verification",
    "fingerprint authentication",
    "identity layer",
  ],
  authors: [{ name: "NeoFace" }],
  icons: {
    icon: "/NeoFaceLogoFinal.png",
    apple: "/NeoFaceLogoFinal.png",
  },
  openGraph: {
    type: "website",
    title: "NeoFace Labs — Biometric Authentication as a Service",
    description:
      "Building the infrastructure where face, fingerprint, and iris intelligence power authentication, trust, and digital identity.",
    siteName: "NeoFace Labs",
    images: [{ url: "/NeoFaceLogoFinal.png" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "NeoFace Labs — Biometric Authentication as a Service",
    description:
      "Building the infrastructure where face, fingerprint, and iris intelligence power authentication, trust, and digital identity.",
    images: ["/NeoFaceLogoFinal.png"],
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${GeistSans.variable} ${GeistMono.variable} font-sans antialiased bg-black`}>
        <SmoothScroll>
          <Providers>
            <NoiseOverlay />
            {children}
            <Toaster
              theme="dark"
              position="bottom-right"
              toastOptions={{
                style: {
                  background: "rgba(10,10,10,0.95)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  color: "#fff",
                  backdropFilter: "blur(20px)",
                  borderRadius: "12px",
                  fontSize: "13px",
                },
              }}
            />
          </Providers>
        </SmoothScroll>
      </body>
    </html>
  );
}
