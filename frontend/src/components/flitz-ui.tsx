import { Link } from "@tanstack/react-router";
import { Menu } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { FlightIcon } from "./flight-icon";
import { ThemeToggle } from "./theme-toggle";
import { useAuth } from "@/lib/auth";
import { riskToken, type RiskLevel } from "@/lib/flitz-data";

export function Logo({ className = "" }: { className?: string }) {
  return (
    <Link to="/" className={`group flex items-center gap-2 ${className}`}>
      <span className="bg-brand flex h-8 w-8 items-center justify-center rounded-xl shadow-glow">
        <FlightIcon className="h-4 w-4 text-primary-foreground transition-transform duration-500 group-hover:translate-x-0.5" />
      </span>
      <span className="font-display text-lg font-extrabold tracking-tight">FLITZZZZ</span>
    </Link>
  );
}

const NAV = [
  { to: "/home", label: "Home" },
  { to: "/flights", label: "Flights" },
  { to: "/predict", label: "Predict" },
  { to: "/rebook", label: "Rebook" },
  { to: "/ops", label: "Crew" },
  { to: "/insights", label: "Insights" },
  { to: "/reports", label: "Reports" },
] as const;

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated, logout, user } = useAuth();

  return (
    <header className="glass sticky top-0 z-50 w-full border-b border-border/50">
      <div className="flex h-16 w-full items-center justify-between gap-4 px-4 sm:px-8 lg:px-12">
        <Logo />
        <nav className="hidden items-center gap-1.5 lg:flex">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="relative rounded-full px-4 py-1.5 text-xs font-semibold text-muted-foreground transition-all duration-300 hover:bg-accent/80 hover:text-foreground"
              activeProps={{
                className:
                  "bg-brand text-primary-foreground font-extrabold shadow-glow scale-[1.05] hover:text-primary-foreground",
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-block text-xs font-semibold text-muted-foreground">
                Hi, <strong className="text-foreground">{user?.name || "Captain"}</strong>
              </span>
              <button
                onClick={() => {
                  logout();
                  window.location.href = "/";
                }}
                className="rounded-full border border-destructive/40 bg-destructive/10 px-4 py-1.5 text-xs font-bold text-destructive transition-colors hover:bg-destructive/20"
              >
                Logout
              </button>
            </div>
          ) : (
            <>
              <Link
                to="/login"
                className="hidden rounded-full border border-border px-4 py-1.5 text-sm font-medium transition-colors hover:bg-accent sm:inline-flex"
              >
                Sign in
              </Link>
              <Link
                to="/signup"
                className="bg-brand hidden rounded-full px-4 py-1.5 text-sm font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.03] sm:inline-flex"
              >
                Sign up
              </Link>
            </>
          )}
          <button
            type="button"
            aria-label="Toggle navigation"
            onClick={() => setOpen((v) => !v)}
            className="glass inline-flex h-9 w-9 items-center justify-center rounded-full lg:hidden"
          >
            <Menu className="h-4 w-4" />
          </button>
        </div>
      </div>
      {open && (
        <div className="glass w-full border-t border-border/40 p-4 lg:hidden">
          <div className="grid gap-1">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                className="rounded-xl px-3.5 py-2.5 text-sm font-medium text-muted-foreground transition-all hover:bg-accent hover:text-foreground"
                activeProps={{
                  className: "bg-brand text-primary-foreground font-extrabold shadow-glow",
                }}
              >
                {item.label}
              </Link>
            ))}
            {!isAuthenticated ? (
              <div className="mt-3 flex flex-col gap-2 pt-3 border-t border-border/40">
                <Link
                  to="/login"
                  onClick={() => setOpen(false)}
                  className="rounded-xl border border-border py-2 text-center text-xs font-semibold"
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  onClick={() => setOpen(false)}
                  className="bg-brand rounded-xl py-2 text-center text-xs font-semibold text-primary-foreground"
                >
                  Sign Up
                </Link>
              </div>
            ) : (
              <div className="mt-3 pt-3 border-t border-border/40">
                <button
                  onClick={() => {
                    logout();
                    setOpen(false);
                    window.location.href = "/";
                  }}
                  className="w-full rounded-xl border border-destructive/40 bg-destructive/10 py-2 text-center text-xs font-bold text-destructive"
                >
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-border bg-card/40 py-12">
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3 pb-8 border-b border-border/40">
          <div>
            <Logo />
            <p className="mt-3 text-xs text-muted-foreground leading-relaxed">
              Predict. Explain. Act. — Transforming Flight Delays Into Proactive Action.
            </p>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              Contact & Support
            </h4>
            <ul className="mt-3 space-y-2 text-xs text-muted-foreground">
              <li>
                📧{" "}
                <a href="mailto:contact@flitzz.ai" className="hover:text-primary transition-colors">
                  contact@flitzz.ai
                </a>
              </li>
              <li>
                📞{" "}
                <a href="tel:+180055535489" className="hover:text-primary transition-colors">
                  +1 (800) 555-FLITZ
                </a>
              </li>
              <li>🏢 San Francisco, CA 94128</li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
              Quick Workspace Links
            </h4>
            <ul className="mt-3 space-y-1.5 text-xs text-muted-foreground">
              <li>
                <Link to="/home" className="hover:text-primary">
                  Home Workspace
                </Link>
              </li>
              <li>
                <Link to="/predict" className="hover:text-primary">
                  Flight Risk Predictor
                </Link>
              </li>
              <li>
                <Link to="/rebook" className="hover:text-primary">
                  AI Passenger Rebooking
                </Link>
              </li>
              <li>
                <Link to="/ops" className="hover:text-primary">
                  Crew & Ops Control
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-6 flex flex-col items-center justify-between gap-3 text-xs text-muted-foreground sm:flex-row">
          <p>
            &copy; {new Date().getFullYear()} Flitzz Aviation Intelligence Inc. All rights reserved.
          </p>
          <p className="font-semibold text-primary">Predict. Explain. Act. ✈️</p>
        </div>
      </div>
    </footer>
  );
}

export function PageShell({
  children,
  eyebrow,
  title,
  description,
}: {
  children: ReactNode;
  eyebrow?: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main className="mx-auto max-w-7xl px-4 pt-12 sm:px-6">
        <header className="mb-10">
          {eyebrow && (
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
              {eyebrow}
            </p>
          )}
          <h1 className="mt-3 text-4xl font-extrabold sm:text-5xl">{title}</h1>
          {description && (
            <p className="mt-3 max-w-2xl text-base text-muted-foreground">{description}</p>
          )}
        </header>
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}

export function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setVisible(true);
      },
      { threshold: 0.15 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      data-visible={visible}
      style={{ transitionDelay: `${delay}ms` }}
      className={`reveal ${className}`}
    >
      {children}
    </div>
  );
}

export function RiskBadge({ level }: { level: RiskLevel }) {
  const token = riskToken(level);
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold"
      style={{
        color: `var(--${token})`,
        background: `color-mix(in oklab, var(--${token}) 14%, transparent)`,
        border: `1px solid color-mix(in oklab, var(--${token}) 32%, transparent)`,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: `var(--${token})` }} />
      {level} risk
    </span>
  );
}

export function GlassCard({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={style}
      className={`glass rounded-3xl p-6 transition-all duration-500 hover:shadow-glow ${className}`}
    >
      {children}
    </div>
  );
}
