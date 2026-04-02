export function ChatEmptyIllustration({ className }: { className?: string }) {
  return (
    <div
      className={`relative mx-auto flex aspect-square w-full max-w-[200px] items-center justify-center ${className ?? ""}`}
      aria-hidden
    >
      <div className="absolute inset-0 animate-pulse-ring rounded-full bg-gradient-to-br from-primary/15 via-violet-500/10 to-teal-500/15 blur-2xl" />
      <svg
        viewBox="0 0 200 200"
        className="relative h-full w-full text-primary drop-shadow-sm"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="100"
          cy="100"
          r="88"
          stroke="currentColor"
          strokeWidth="1"
          strokeOpacity="0.2"
          className="animate-float-soft"
        />
        <circle
          cx="100"
          cy="100"
          r="68"
          stroke="url(#c1)"
          strokeWidth="1.5"
          strokeDasharray="6 10"
          className="animate-float-soft"
          style={{ animationDelay: "0.2s" }}
        />
        <circle
          cx="100"
          cy="100"
          r="48"
          stroke="url(#c1)"
          strokeWidth="2"
          strokeOpacity="0.85"
        />
        <path
          d="M100 62 L128 118 L72 118 Z"
          stroke="url(#c1)"
          strokeWidth="2"
          strokeLinejoin="round"
          fill="currentColor"
          fillOpacity="0.08"
        />
        <circle cx="100" cy="100" r="6" fill="currentColor" fillOpacity="0.9" />
        <defs>
          <linearGradient id="c1" x1="40" y1="40" x2="170" y2="170" gradientUnits="userSpaceOnUse">
            <stop stopColor="#4f46e5" />
            <stop offset="0.55" stopColor="#7c3aed" />
            <stop offset="1" stopColor="#0d9488" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}
