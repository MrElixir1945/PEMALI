"use client";

import { useEffect } from "react";

interface ErrorBoundaryProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function DashboardError({ error, reset }: ErrorBoundaryProps) {
  useEffect(() => {
    console.error("[Dashboard Error]", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-8">
      <div className="text-4xl mb-4">⚠️</div>
      <h2 className="text-xl font-semibold text-[var(--pemali-text-primary)] mb-2">
        Terjadi Gangguan
      </h2>
      <p className="text-sm text-[var(--pemali-text-secondary)] mb-6 max-w-md">
        Ada masalah saat memuat dashboard. Ini bisa jadi karena koneksi internet
        atau server backend sedang tidak aktif.
      </p>
      <button
        onClick={reset}
        className="px-5 py-2.5 bg-[var(--pemali-accent)] hover:bg-[var(--pemali-accent)]/90 text-white rounded-lg text-sm font-semibold transition-all"
      >
        Coba Lagi
      </button>
    </div>
  );
}
