export default function DashboardLoading() {
  return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-[var(--pemali-accent)] border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-[var(--pemali-text-muted)] font-mono uppercase tracking-widest">
          Memuat Dashboard...
        </span>
      </div>
    </div>
  );
}
