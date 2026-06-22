"use client";
import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => { console.error(error); }, [error]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center space-y-4">
        <div className="flex justify-center">
          <div className="w-16 h-16 rounded-2xl bg-error/15 border border-error/30 flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-error" />
          </div>
        </div>
        <h1 className="text-xl font-bold text-white">Something went wrong</h1>
        <p className="text-text-muted text-sm max-w-sm">{error.message}</p>
        <Button onClick={reset} variant="outline">Try again</Button>
      </div>
    </div>
  );
}
