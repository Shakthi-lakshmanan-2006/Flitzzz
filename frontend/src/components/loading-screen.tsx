import { useEffect, useState } from "react";

import { FlightIcon, FLIGHT_ICON_PATH } from "@/components/flight-icon";

const STEPS = ["Loading flight data", "Building airport network", "Warming prediction engine"];

export function LoadingScreen({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / 2200);
      setProgress(k * 100);
      setStep(Math.min(STEPS.length - 1, Math.floor(k * STEPS.length)));
      if (k < 1) raf = requestAnimationFrame(tick);
      else onDone();
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [onDone]);

  return (
    <div className="bg-hero fixed inset-0 z-[100] flex flex-col items-center justify-center gap-8">
      <div className="flex items-center gap-3">
        <span className="bg-brand flex h-10 w-10 items-center justify-center rounded-2xl shadow-glow">
          <FlightIcon className="h-5 w-5 text-primary-foreground" />
        </span>
        <span className="font-display text-2xl font-extrabold tracking-tight">FLITZZZZ</span>
      </div>

      <div className="relative w-[min(420px,80vw)]">
        <svg viewBox="0 0 420 60" className="w-full">
          <path
            id="loadPath"
            d="M 10 45 Q 210 -10 410 45"
            fill="none"
            stroke="var(--grid-line)"
            strokeWidth="2"
            strokeDasharray="5 8"
          />
          <g>
            <path d={FLIGHT_ICON_PATH} fill="var(--primary)">
              <animateMotion
                dur="2.2s"
                repeatCount="indefinite"
                rotate="auto"
                path="M 10 45 Q 210 -10 410 45"
              />
            </path>
          </g>
        </svg>
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-muted">
          <div className="bg-brand h-full rounded-full" style={{ width: `${progress}%` }} />
        </div>
        <p className="mt-3 text-center text-xs uppercase tracking-[0.22em] text-muted-foreground">
          {STEPS[step]}…
        </p>
      </div>
    </div>
  );
}
