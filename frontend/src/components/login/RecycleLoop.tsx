export function RecycleLoop() {
  return (
    <svg aria-label="Recycling loop" role="img" viewBox="0 0 80 80" className="h-16 w-16 shrink-0">
      <defs>
        <linearGradient id="recycle-gradient" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#31A8E0" /><stop offset="1" stopColor="#94C11F" />
        </linearGradient>
      </defs>
      <circle cx="40" cy="40" r="27" fill="none" stroke="white" strokeOpacity=".12" strokeWidth="1" />
      <g className="animate-orbit">
        <circle cx="40" cy="13" r="3.5" fill="#31A8E0" />
        <circle cx="63" cy="53" r="3.5" fill="#3AAA35" />
        <circle cx="17" cy="53" r="3.5" fill="#94C11F" />
        <path d="M40 13a27 27 0 0 1 23 40M63 53a27 27 0 0 1-46 0M17 53a27 27 0 0 1 23-40" fill="none" stroke="url(#recycle-gradient)" strokeWidth="1.5" strokeDasharray="3 4" />
      </g>
      <path d="m36 36 8 4-8 4v-3h-7v-2h7z" fill="white" opacity=".8" />
    </svg>
  );
}

