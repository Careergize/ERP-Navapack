import { RecycleLoop } from "./RecycleLoop";
import { WovenBackground } from "./WovenBackground";

export function BrandPanel() {
  return (
    <section className="relative hidden min-h-screen overflow-hidden bg-navy text-white lg:flex lg:w-[55%] lg:flex-col lg:justify-between lg:p-12 xl:p-16">
      <WovenBackground />
      <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full opacity-20" viewBox="0 0 700 900" preserveAspectRatio="none">
        <path d="M450 540C535 410 590 300 680 220M450 540C550 505 605 495 700 455M450 540C550 600 615 690 700 790" fill="none" stroke="#31A8E0" strokeDasharray="2 10" strokeWidth="1" />
        <circle className="animate-pulse-point" cx="450" cy="540" r="5" fill="#94C11F" />
        <circle cx="450" cy="540" r="13" fill="none" stroke="#94C11F" strokeOpacity=".35" />
      </svg>

      <div className="relative z-10">
        <div className="inline-flex rounded-xl bg-white px-5 py-3 shadow-xl shadow-black/10">
          <img src="/assets/Nava-logo.png" alt="Nava Pack" className="h-10 w-auto max-w-[220px] object-contain" />
        </div>
        <p className="mt-8 max-w-md text-sm font-medium uppercase tracking-[.28em] text-teal">Global Movement, Local Precision</p>
        <h1 className="mt-5 max-w-xl text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">Packaging that moves the world forward.</h1>
        <p className="mt-6 max-w-lg text-base leading-7 text-white/65">From woven sacks and bags to recycled granules, Nava Pack connects responsible production with dependable delivery.</p>
      </div>

      <div className="relative z-10 flex items-center gap-4">
        <RecycleLoop />
        <p className="max-w-xs text-sm leading-6 text-white/60">Waste becomes raw material again — keeping every cycle in motion.</p>
      </div>
    </section>
  );
}

