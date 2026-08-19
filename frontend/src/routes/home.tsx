import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  CloudRain,
  Gauge,
  Globe,
  History,
  Layers,
  LogOut,
  Plane,
  RefreshCw,
  Route as RouteIcon,
  Search,
  Settings as SettingsIcon,
  ShieldAlert,
  Sparkles,
  Ticket,
  User as UserIcon,
  Users,
  Wrench,
  Zap,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { FlightMap, type MapRoute } from "@/components/flight-map";
import { GlassCard, Reveal, SiteFooter, SiteHeader } from "@/components/flitz-ui";
import { useAuth } from "@/lib/auth";
import { KPIS } from "@/lib/flitz-data";

export const Route = createFileRoute("/home")({
  head: () => ({
    meta: [
      { title: "Flitzz — Flight Delay Prediction Home Workspace" },
      {
        name: "description",
        content:
          "Predictive platform designed to revolutionize airline operations by predicting delays, explaining root causes, and automated rebooking.",
      },
    ],
  }),
  component: ProtectedHome,
});

const MAP_ROUTES: MapRoute[] = [
  { origin: "JFK", destination: "LHR", riskScore: 28 },
  { origin: "DXB", destination: "SIN", riskScore: 18 },
  { origin: "LAX", destination: "HND", riskScore: 32 },
  { origin: "SFO", destination: "SYD", riskScore: 22 },
  { origin: "SEA", destination: "ATL", riskScore: 41 },
  { origin: "DEL", destination: "FRA", riskScore: 64 },
  { origin: "ATL", destination: "GRU", riskScore: 58 },
  { origin: "MIA", destination: "BOS", riskScore: 72 },
  { origin: "ORD", destination: "DEN", riskScore: 68 },
  { origin: "BOM", destination: "LHR", riskScore: 89 },
  { origin: "CDG", destination: "ORD", riskScore: 84 },
  { origin: "DFW", destination: "JFK", riskScore: 91 },
];

const CAROUSEL_CARDS = [
  {
    id: "drivers",
    title: "Delay Drivers",
    icon: CloudRain,
    badge: "Multi-Stream Feature Signals",
    description:
      "Visual breakdown of weather, traffic congestion, and temporal features driving risk models.",
    details: [
      "Real-time precipitation & visibility indexing",
      "Runway & airspace capacity utilization metrics",
      "Cascading aircraft rotation & slot pressures",
    ],
    actionText: "Explore Signals",
    actionLink: "/predict",
  },
  {
    id: "risk-scores",
    title: "Delay Risk Scores",
    icon: Gauge,
    badge: "LightGBM Predictive Engine",
    description:
      "Dynamic LightGBM risk probabilities (0–100%) split into Low, Medium, and High bands.",
    details: [
      "Low Risk (<50%): On-time monitoring",
      "Medium Risk (50–75%): Manual dispatch review",
      "High Risk (>75%): Automated intervention trigger",
    ],
    actionText: "View Dashboard",
    actionLink: "/dashboard",
  },
  {
    id: "reasons",
    title: "Flight Delay Reasons",
    icon: Sparkles,
    badge: "Explainable AI (SHAP)",
    description:
      "Explainable AI (SHAP) paired with LLM natural language summaries for dispatchers and passengers.",
    details: [
      "Feature contribution bar charts per flight",
      "Automated dispatcher summary briefings",
      "Historical carrier benchmark comparisons",
    ],
    actionText: "View SHAP Insights",
    actionLink: "/insights",
  },
  {
    id: "rebooking",
    title: "AI Rebooking",
    icon: Ticket,
    badge: "Automated Passenger Recovery",
    description:
      "Automated passenger alternative matching ranked by arrival time, seat availability, and fare delta.",
    details: [
      "1-Click mobile boarding pass generation",
      "Partner airline seat availability search",
      "Complimentary $45 lounge voucher issuance",
    ],
    actionText: "Open AI Rebooking",
    actionLink: "/rebook",
  },
  {
    id: "crew-ops",
    title: "Crew & Ground Operations",
    icon: Users,
    badge: "Manager Control Center",
    description:
      "Real-time crew duty health monitoring, gate turnaround tracking, and standby pool management.",
    details: [
      "FAA legal duty hour compliance tracking",
      "Gate turnaround countdown timers",
      "1-Click standby crew roster swaps",
    ],
    actionText: "Manage Ops & Crew",
    actionLink: "/ops",
  },
];

function ProtectedHome() {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const carouselRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const [isPaused, setIsPaused] = useState(false);

  // Auto Move: Auto-scroll Feature Capabilities cards every 3 seconds
  useEffect(() => {
    if (isPaused) return;
    const interval = setInterval(() => {
      if (!carouselRef.current) return;
      const { scrollLeft, scrollWidth, clientWidth } = carouselRef.current;
      if (scrollLeft + clientWidth >= scrollWidth - 20) {
        carouselRef.current.scrollTo({ left: 0, behavior: "smooth" });
      } else {
        carouselRef.current.scrollBy({ left: 360, behavior: "smooth" });
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [isPaused]);

  if (!isAuthenticated || !user) {
    return null;
  }

  function scrollCarousel(direction: "left" | "right") {
    if (!carouselRef.current) return;
    const scrollAmount = 360;
    carouselRef.current.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      {/* HERO & MAP CONTINUOUS BACKGROUND WRAPPER */}
      <div className="relative overflow-hidden bg-hero pb-16 pt-12 sm:pt-20">
        {/* Background image set to 80% visibility & 20% blur balance covering up to the map */}
        <div
          className="absolute inset-0 bg-cover bg-center opacity-80 filter blur-[2px] scale-105"
          style={{
            backgroundImage: "url('/hero-bg.jpg')",
          }}
          aria-hidden
        />
        <div
          className="absolute inset-0 bg-gradient-to-b from-background/30 via-background/50 to-background"
          aria-hidden
        />
        <div className="grid-lines absolute inset-0 opacity-30" aria-hidden />

        {/* ==========================================
            1. HERO HEADER & VALUE PROPOSITION
            ========================================== */}
        <div className="relative mx-auto max-w-7xl px-4 sm:px-6">
          <div className="mx-auto max-w-4xl text-center">
            {/* HEADLINE */}
            <Reveal>
              <h1 className="text-4xl font-black tracking-tight sm:text-6xl lg:text-7xl">
                Flitzz - Flight Delay Prediction
              </h1>
            </Reveal>

            {/* SUBTITLE */}
            <Reveal delay={120}>
              <p className="mx-auto mt-6 max-w-3xl text-lg leading-relaxed text-muted-foreground sm:text-xl">
                A predictive platform designed to revolutionize airline operations, Flitzz
                proactively assists airlines and passengers along with its crew by predicting
                delays, explaining their root causes, managing operations and rebooking, and
                minimizing disruption.
              </p>
            </Reveal>
            {/* CENTERED ACTION BUTTONS */}
            <Reveal delay={180}>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link
                  to="/predict"
                  className="bg-brand inline-flex items-center gap-2 rounded-full px-6 py-3 text-xs font-bold text-primary-foreground shadow-glow transition-transform hover:scale-[1.03]"
                >
                  Predict a Flight <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/flights"
                  className="glass inline-flex items-center gap-2 rounded-full px-6 py-3 text-xs font-bold transition-transform hover:scale-[1.03]"
                >
                  Live Flight Radar
                </Link>
                <Link
                  to="/rebook"
                  className="glass inline-flex items-center gap-2 rounded-full px-6 py-3 text-xs font-bold transition-transform hover:scale-[1.03]"
                >
                  AI Rebooking
                </Link>
                <Link
                  to="/ops"
                  className="glass inline-flex items-center gap-2 rounded-full px-6 py-3 text-xs font-bold transition-transform hover:scale-[1.03]"
                >
                  Ops Control
                </Link>
              </div>
            </Reveal>
          </div>
        </div>

        {/* ==========================================
            2. INTERACTIVE GLOBAL ROUTE MAP (GEOSPATIAL AIR NETWORK)
            ========================================== */}
        <section className="relative mx-auto max-w-7xl px-4 pt-16 sm:px-6">
          <Reveal>
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                  GEOSPATIAL AIR NETWORK
                </span>
                <h2 className="text-2xl font-extrabold sm:text-4xl text-foreground">
                  Interactive Global Route Map
                </h2>
              </div>

              {/* 3-COLOR VISUAL STATUS LEGEND */}
              <div className="flex flex-wrap items-center gap-4 text-xs font-medium">
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: "var(--risk-low)" }}
                  />
                  <span className="text-muted-foreground">Low Risk (&lt;50%)</span>
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: "var(--risk-medium)" }}
                  />
                  <span className="text-muted-foreground">Medium Risk (50–75%)</span>
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: "var(--risk-high)" }}
                  />
                  <span className="text-muted-foreground">High Risk (&gt;75%)</span>
                </span>
              </div>
            </div>

            {/* FLIGHT MAP WITH USER's UPLOADED 3RD BLUE NETWORK WORLD MAP */}
            <FlightMap routes={MAP_ROUTES} height={520} showLegend={true} animate={true} />
          </Reveal>
        </section>
      </div>

      {/* ==========================================
          3. FEATURE CAROUSEL CARDS (HORIZONTAL SCROLL VIEW)
          ========================================== */}
      <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6">
        <Reveal>
          <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                Operational Modules
              </span>
              <h2 className="text-2xl font-extrabold sm:text-3xl">Feature Capabilities</h2>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => scrollCarousel("left")}
                aria-label="Scroll carousel left"
                className="glass flex h-10 w-10 items-center justify-center rounded-full transition-transform hover:scale-105 active:scale-95"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button
                onClick={() => scrollCarousel("right")}
                aria-label="Scroll carousel right"
                className="glass flex h-10 w-10 items-center justify-center rounded-full transition-transform hover:scale-105 active:scale-95"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div
            ref={carouselRef}
            onMouseEnter={() => setIsPaused(true)}
            onMouseLeave={() => setIsPaused(false)}
            onTouchStart={() => setIsPaused(true)}
            onTouchEnd={() => setIsPaused(false)}
            className="no-scrollbar flex gap-6 overflow-x-auto scroll-smooth pb-6 pt-2"
          >
            {CAROUSEL_CARDS.map((card, idx) => {
              const Icon = card.icon;
              return (
                <GlassCard
                  key={card.id}
                  className="group relative flex min-w-[320px] max-w-[350px] flex-col justify-between flex-shrink-0 overflow-hidden border-border/70 shadow-elevated transition-all duration-500 hover:scale-105 hover:-translate-y-2.5 hover:border-primary hover:shadow-glow"
                  style={{
                    animationDelay: `${idx * 150}ms`,
                  }}
                >
                  {/* POP GLOW ACCENT BAR */}
                  <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary/30 via-primary to-primary/30 opacity-0 transition-opacity duration-500 group-hover:opacity-100" />

                  <div>
                    <div className="flex items-center justify-between">
                      <span className="bg-brand flex h-10 w-10 items-center justify-center rounded-xl shadow-glow transition-transform duration-500 group-hover:rotate-6 group-hover:scale-110">
                        <Icon className="h-5 w-5 text-primary-foreground" />
                      </span>
                      <span className="rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary border border-primary/20 group-hover:border-primary/50 transition-colors">
                        {card.badge}
                      </span>
                    </div>

                    <h3 className="mt-5 text-xl font-bold group-hover:text-primary transition-colors">
                      {card.title}
                    </h3>
                    <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                      {card.description}
                    </p>

                    <div className="mt-4 space-y-2 border-t border-border/40 pt-3">
                      {card.details.map((item) => (
                        <div
                          key={item}
                          className="flex items-start gap-2 text-xs text-foreground font-medium"
                        >
                          <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-primary" />
                          <span>{item}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-border/40">
                    <Link
                      to={card.actionLink}
                      className="glass inline-flex w-full items-center justify-center gap-2 rounded-full py-2.5 text-xs font-semibold transition-all duration-300 group-hover:bg-primary group-hover:text-primary-foreground group-hover:shadow-glow"
                    >
                      {card.actionText}{" "}
                      <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
                    </Link>
                  </div>
                </GlassCard>
              );
            })}
          </div>
        </Reveal>
      </section>

      <SiteFooter />
    </div>
  );
}
