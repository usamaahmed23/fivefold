export function SideBanner() {
  return (
    <div className="relative flex overflow-hidden rounded-md text-[10px] font-semibold tracking-[0.18em] shadow-sm ring-1 ring-border sm:text-xs sm:tracking-[0.35em]">
      <div className="relative flex-1 bg-gradient-to-r from-blue-600/90 via-blue-500/80 to-blue-500/60 px-3 py-2 text-white sm:px-4">
        <span className="relative z-10">BLUE SIDE</span>
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/10 to-transparent" />
      </div>
      <div className="relative flex-1 bg-gradient-to-l from-red-600/90 via-red-500/80 to-red-500/60 px-3 py-2 text-right text-white sm:px-4">
        <span className="relative z-10">RED SIDE</span>
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/10 to-transparent" />
      </div>
    </div>
  );
}
