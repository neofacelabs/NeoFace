import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-grid opacity-40 pointer-events-none" />
      <div className="text-center relative">
        <p className="text-7xl font-black gradient-text mb-4">404</p>
        <h1 className="text-2xl font-bold text-white mb-2">Page not found</h1>
        <p className="text-text-muted mb-8">This page doesn't exist or has been moved.</p>
        <Link href="/" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-accent-violet/20 border border-accent-violet/30 text-accent-soft hover:bg-accent-violet/30 transition-all text-sm font-medium">
          Back to home
        </Link>
      </div>
    </div>
  );
}
