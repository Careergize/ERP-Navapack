export function WovenBackground() {
  return (
    <svg aria-hidden="true" className="pointer-events-none absolute inset-0 h-full w-full opacity-[.13]" preserveAspectRatio="none">
      <defs>
        <pattern id="woven-grid" width="32" height="32" patternUnits="userSpaceOnUse" patternTransform="rotate(8)">
          <path d="M0 0V32 M16 0V32 M0 0H32 M0 16H32" fill="none" stroke="white" strokeWidth=".65" />
        </pattern>
      </defs>
      <rect className="animate-weave" x="-64" y="-64" width="calc(100% + 128px)" height="calc(100% + 128px)" fill="url(#woven-grid)" />
    </svg>
  );
}

