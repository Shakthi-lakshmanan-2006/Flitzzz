import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  CloudRain,
  Cpu,
  Gauge,
  Heart,
  Globe,
  Layers,
  Mail,
  Plane,
  Quote,
  RefreshCw,
  Route as RouteIcon,
  ShieldCheck,
  Sparkles,
  Ticket,
  UserCheck,
  Users,
  Wrench,
  Zap,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { FlightIcon } from "@/components/flight-icon";
import { FlightMap, type MapRoute } from "@/components/flight-map";
import { GlassCard, Reveal, SiteFooter, SiteHeader } from "@/components/flitz-ui";
import { LoadingScreen } from "@/components/loading-screen";
import { KPIS } from "@/lib/flitz-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Flitzz — Flight Delay Prediction & Operational Intelligence" },
      {
        name: "description",
        content:
          "Flitzz is an AI-powered flight delay prediction platform providing root cause explainability, automated passenger rebooking, and crew management.",
      },
    ],
  }),
  component: PublicLanding,
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

const DETAILED_SERVICES = [
  {
    step: "01",
    id: "predictive-ai",
    tabTitle: "01. AI Delay Risk Scoring",
    title: "AI Delay Risk Scoring & Machine Learning Predictions",
    tag: "XGBoost + LightGBM Prediction Engine",
    icon: Gauge,
    description:
      "Flitzz uses two complementary machine learning models: XGBoost classification estimates the probability of a 15+ minute delay, while LightGBM regression predicts the expected arrival delay in minutes.",
    highlights: [
      "XGBoost classification estimates the probability of a 15+ minute delay",
      "LightGBM regression predicts the expected arrival delay in minutes",
      "Model performance is evaluated using a dedicated validation dataset",
    ],
    badgeColor: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    actionText: "Try Live Predictor",
    actionLink: "/predict",
  },
  {
    step: "02",
    id: "explainable-ai",
    tabTitle: "02. Root Cause SHAP",
    title: "Root Cause Explainability & SHAP Analytics",
    tag: "Explainable AI (XAI)",
    icon: Sparkles,
    description:
      "Go beyond black-box predictions. Flitzz uses SHAP (SHapley Additive exPlanations) to identify the strongest factors influencing each flight delay prediction and present them as concise operational explanations.",
    highlights: [
      "Identifies the strongest factors influencing delay probability",
      "Explains the major factors contributing to predicted delay minutes",
      "Converts model contributions into concise operational insights",
    ],
    badgeColor: "bg-purple-500/10 text-purple-500 border-purple-500/20",
    actionText: "Explore SHAP Insights",
    actionLink: "/insights",
  },
  {
    step: "03",
    id: "ai-rebooking",
    tabTitle: "03. AI Rebooking",
    title: "Automated Passenger AI Rebooking & Protection",
    tag: "Passenger Recovery System",
    icon: Ticket,
    description:
      "When high-risk delay thresholds (>75%) are breached, Flitzz automatically searches partner airline inventories and matches impacted passengers to optimal alternative connections ranked by arrival time, seat availability, and fare delta.",
    highlights: [
      "1-Click mobile boarding pass generation with zero manual counter queues",
      "Automated baggage transfer protection and connection safety guarantees",
      "Instant issuance of complimentary $45 Executive Lounge & refreshment vouchers",
    ],
    badgeColor: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    actionText: "Test AI Rebooking",
    actionLink: "/rebook",
  },
  {
    step: "04",
    id: "ops-management",
    tabTitle: "04. Ops & Crew Control",
    title: "Airline Operations & Crew Duty Management",
    tag: "Manager Dispatch Control",
    icon: Users,
    description:
      "Empower flight managers and dispatchers with an executive operational dashboard to monitor crew duty legal limits, gate turnaround countdowns, and relief aircraft dispatch in real time.",
    highlights: [
      "Real-time FAA legal flight hour compliance tracking and fatigue risk index alerts",
      "Turnaround countdown monitors across fueling, baggage loading, catering, and cleaning",
      "1-Click standby crew roster swaps with instant mobile notification triggers",
    ],
    badgeColor: "bg-rose-500/10 text-rose-500 border-rose-500/20",
    actionText: "Open Ops Control",
    actionLink: "/ops",
  },
  {
    step: "05",
    id: "passenger-notifications",
    tabTitle: "05. Email & SMS Alerts",
    title: "Automated Email & SMS Passenger Triggers",
    tag: "Proactive Communication",
    icon: Mail,
    description:
      "Eliminate airport terminal confusion by automatically dispatching personalized, multi-channel email and SMS alerts to travelers as soon as a delay risk is confirmed.",
    highlights: [
      "Clear, transparent explanation of delay root cause sent directly to traveler handsets",
      "1-Click mobile portal link for instant seat confirmation on alternative flights",
      "Digital QR vouchers accepted at airport partner lounges and dining venues",
    ],
    badgeColor: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    actionText: "View Email Triggers",
    actionLink: "/rebook",
  },
  {
    step: "06",
    id: "geospatial-radar",
    tabTitle: "06. Global Air Radar",
    title: "Real-time Air Network Geospatial Radar",
    tag: "Live Airspace Tracking",
    icon: Globe,
    description:
      "Visualize global airspace risk across major international aviation hubs using our high-definition 3D satellite map featuring live animated flight trajectories and 3-color risk protocols.",
    highlights: [
      "🟢 Green (<50%), 🟡 Yellow (50–75%), and 🔴 Red (>75%) visual risk protocol",
      "Live animated custom aircraft markers traveling along curved flight arcs",
      "Pulsing airport radar nodes with real-time hub congestion overlays",
    ],
    badgeColor: "bg-cyan-500/10 text-cyan-500 border-cyan-500/20",
    actionText: "Inspect Global Map",
    actionLink: "/dashboard",
  },
];

const STAKEHOLDERS = [
  {
    id: "managers",
    tabLabel: "Airline Managers",
    name: "Airline Operations Managers & Dispatchers",
    roleBadge: "Operational Command Center",
    icon: Zap,
    stat: "Proactive Delay Management",
    statSub: "Operational Decision Support",
    heroImage:
      "https://images.unsplash.com/photo-1551836022-d5d88e9218df?q=80&w=1200&auto=format&fit=crop",
    headline: "Proactively Eliminate Turnaround Bottlenecks Before They Cascade",
    description:
      "Flight managers and dispatchers gain real-time visibility into high-risk departures, enabling automated 1-click relief aircraft dispatch and gate re-allocations.",
    keyPoints: [
      "LightGBM delay probability scoring (0–100%) for every scheduled departure",
      "Automated natural language dispatcher briefings & SHAP driver breakdowns",
      "Instant 1-click standby crew reassignment and turnaround fast-tracking",
    ],
    actionText: "Explore Operations Dashboard",
    actionLink: "/ops",
  },
  {
    id: "crews",
    tabLabel: "Flight Crews",
    name: "Flight Captains & Cabin Crew Members",
    roleBadge: "Flight Safety & Crew Health",
    icon: UserCheck,
    stat: "Crew Duty Monitoring",
    statSub: "Operational Safety Support",
    heroImage:
      "https://images.unsplash.com/photo-1520437358207-323b43b5752b?q=80&w=1200&auto=format&fit=crop",
    headline: "Real-Time Roster Transparency & FAA Duty Limit Safety Tracking",
    description:
      "Captains and flight attendants can monitor legal duty hour buffers, receive fatigue risk notifications, and benefit from automated standby crew swaps.",
    keyPoints: [
      "Live legal flight hour countdown timers per crew assignment",
      "Automated fatigue index risk alerts before stepping into the cockpit",
      "Seamless 1-click standby crew roster swaps with immediate notification",
    ],
    actionText: "View Crew Scheduling",
    actionLink: "/ops",
  },
  {
    id: "passengers",
    tabLabel: "Passengers",
    name: "Passengers & Global Travelers",
    roleBadge: "Stress-Free Travel Recovery",
    icon: Heart,
    stat: "Proactive Passenger Support",
    statSub: "Automated Recovery Assistance",
    heroImage:
      "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=1200&auto=format&fit=crop",
    headline: "Zero-Stress Travel: Rebooked Before Reaching the Gate",
    description:
      "Passengers receive instant automated email and SMS delay notices containing 1-click rebooking passes and complimentary airport lounge vouchers.",
    keyPoints: [
      "Automated delay email alerts with exact root cause explanations",
      "1-Click digital boarding pass issuance on optimal alternate flights",
      "Complimentary $45 Executive Lounge & refreshment voucher codes",
    ],
    actionText: "Try AI Rebooking",
    actionLink: "/rebook",
  },
  {
    id: "regulators",
    tabLabel: "Airport Regulators",
    name: "Airport Hub Regulators & Ground Controllers",
    roleBadge: "Airspace & Gate Optimization",
    icon: ShieldCheck,
    stat: "Network Risk Visibility",
    statSub: "Airport Operations Intelligence",
    heroImage:
      "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?q=80&w=1200&auto=format&fit=crop",
    headline: "Maximized Runway Throughput & Reduced Gate Holding Times",
    description:
      "Airport controllers gain geospatial congestion visibility across peak departure windows, reducing ground holding queues and environmental fuel burn.",
    keyPoints: [
      "Geospatial air network radar map with 3-color status protocol",
      "Optimized gate allocation and turnaround countdown timers",
      "Predictive runway queue management across global hubs",
    ],
    actionText: "View Network Map",
    actionLink: "/dashboard",
  },
];

function PublicLanding() {
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);
  const [activeService, setActiveService] = useState(0);
  const [activeStakeholder, setActiveStakeholder] = useState(0);
  const [contactSubmitted, setContactSubmitted] = useState(false);
  const [contactForm, setContactForm] = useState({
    name: "",
    email: "",
    org: "",
    message: "",
  });
  const servicesRef = useRef<HTMLDivElement>(null);

  function handleContactSubmit(e: React.FormEvent) {
    e.preventDefault();
    setContactSubmitted(true);
    setTimeout(() => {
      setContactForm({ name: "", email: "", org: "", message: "" });
    }, 4000);
  }

  useEffect(() => {
    if (loading) return;
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const k = Math.min(1, (t - start) / 1600);
      setCount(KPIS.flightsAnalyzed * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [loading]);

  // Automatic 3-Second Service Showcase Rotation
  useEffect(() => {
    if (loading) return;
    const interval = setInterval(() => {
      setActiveService((prev) => (prev + 1) % DETAILED_SERVICES.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [loading]);

  // Automatic 5-Second Stakeholder Carousel Rotation
  useEffect(() => {
    if (loading) return;
    const interval = setInterval(() => {
      setActiveStakeholder((prev) => (prev + 1) % STAKEHOLDERS.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [loading]);

  function scrollToServices() {
    if (servicesRef.current) {
      servicesRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }

  const activeServiceData = DETAILED_SERVICES[activeService]!;
  const ActiveServiceIcon = activeServiceData.icon;

  const activeStakeholderData = STAKEHOLDERS[activeStakeholder]!;
  const StakeholderIcon = activeStakeholderData.icon;

  return (
    <>
      {loading && <LoadingScreen onDone={() => setLoading(false)} />}
      <div className="min-h-screen bg-background">
        {/* ==========================================
            SECTION 1: HERO HEADER & VALUE PROPOSITION (VIDEO BACKGROUND)
            ========================================== */}
        <section className="relative overflow-hidden bg-hero pb-24 pt-20 sm:pt-28">
          {/* User's uploaded background video for Public Landing Page */}
          <video
            autoPlay
            loop
            muted
            playsInline
            className="absolute inset-0 h-full w-full object-cover opacity-80 filter blur-[1px] scale-105"
          >
            <source src="/landing-video.mp4" type="video/mp4" />
          </video>
          <div
            className="absolute inset-0 bg-gradient-to-b from-background/30 via-background/50 to-background"
            aria-hidden
          />
          <div className="grid-lines absolute inset-0 opacity-30" aria-hidden />

          <div className="relative mx-auto max-w-7xl px-4 sm:px-6">
            <div className="mx-auto max-w-4xl text-center">
              {/* WEBSITE MOTTO BADGE */}
              <Reveal>
                <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/40 bg-card/80 px-4 py-1.5 backdrop-blur-md shadow-glow">
                  <Sparkles className="h-4 w-4 text-primary" />
                  <span className="font-display text-xs font-extrabold uppercase tracking-[0.18em] text-primary">
                    Predict. Explain. Act. — Transforming Flight Delays Into Proactive Action
                  </span>
                </div>
              </Reveal>

              {/* HEADLINE */}
              <Reveal delay={60}>
                <h1 className="text-4xl font-black tracking-tight sm:text-6xl lg:text-7xl">
                  Flitzz - Flight Delay Prediction
                </h1>
              </Reveal>

              {/* SHORT PROJECT DESCRIPTION */}
              <Reveal delay={120}>
                <p className="mx-auto mt-6 max-w-3xl text-lg leading-relaxed text-muted-foreground sm:text-xl">
                  A predictive platform designed to revolutionize airline operations, Flitzz
                  proactively assists airlines and passengers along with its crew by predicting
                  delays, explaining their root causes, managing operations and rebooking, and
                  minimizing disruption.
                </p>
              </Reveal>

              {/* ACTION BUTTONS */}
              <Reveal delay={180}>
                <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
                  <Link
                    to="/signup"
                    className="bg-brand inline-flex items-center gap-2 rounded-full px-7 py-3.5 text-sm font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.03]"
                  >
                    Get Started <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    to="/login"
                    className="glass inline-flex items-center gap-2 rounded-full px-6 py-3.5 text-sm font-semibold transition-transform duration-300 hover:scale-[1.03]"
                  >
                    Sign In
                  </Link>
                </div>
              </Reveal>

              {/* SCROLL DOWN FEATURE / BUTTON */}
              <Reveal delay={240}>
                <div className="mt-14 flex flex-col items-center">
                  <button
                    onClick={scrollToServices}
                    aria-label="Scroll down to explore platform services auto-advancing every 3 seconds"
                    className="group glass flex flex-col items-center gap-2 rounded-full px-5 py-2.5 text-xs font-semibold transition-all duration-300 hover:border-primary hover:shadow-glow"
                  >
                    <span className="text-muted-foreground group-hover:text-foreground">
                      Scroll Down to View Automated 3-Second Services Showcase
                    </span>
                    <ChevronDown className="h-4 w-4 animate-bounce text-primary" />
                  </button>
                </div>
              </Reveal>
            </div>

            {/* Quick KPI Bar */}
            <div className="mt-16 grid gap-4 sm:grid-cols-3">
              <GlassCard>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Flights Analyzed
                </p>
                <p className="font-display mt-2 text-3xl font-extrabold tabular-nums">
                  {Math.round(count).toLocaleString()}
                </p>
              </GlassCard>
              <GlassCard>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Model Accuracy
                </p>
                <p className="font-display mt-2 text-3xl font-extrabold tabular-nums">
                  84%
                </p>
              </GlassCard>
              <GlassCard>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Network Delay Mitigation
                </p>
                <p className="font-display mt-2 text-3xl font-extrabold tabular-nums">
                  {KPIS.delayRate}%
                </p>
              </GlassCard>
            </div>
          </div>
        </section>

        {/* ==========================================
            SECTION 2: AUTOMATED 3-SECOND SERVICE SHOWCASE (AUTO-ADVANCE 3 SEC PAUSE)
            ========================================== */}
        <section ref={servicesRef} className="mx-auto max-w-7xl px-4 py-24 sm:px-6">
          <Reveal>
            <div className="text-center max-w-3xl mx-auto mb-14">
              <span className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
                Comprehensive Capabilities
              </span>
              <h2 className="mt-3 text-3xl font-extrabold sm:text-5xl">
                Services Provided by Flitzz
              </h2>
              <p className="mt-3 text-muted-foreground text-base">
                Automatically advances every 3 seconds. Click any service tab below to jump to that
                module.
              </p>
            </div>
          </Reveal>

          {/* 6 Step Service Pill Tabs with 3-Second Progress Timer */}
          <div className="mb-8 overflow-x-auto no-scrollbar">
            <div className="flex gap-2 min-w-max pb-2">
              {DETAILED_SERVICES.map((srv, idx) => {
                const isActive = idx === activeService;
                return (
                  <button
                    key={srv.id}
                    onClick={() => setActiveService(idx)}
                    className={`relative overflow-hidden rounded-2xl px-4 py-3 text-left transition-all ${
                      isActive
                        ? "glass border-primary bg-primary/10 shadow-glow"
                        : "border border-border/50 hover:bg-accent/40"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <srv.icon
                        className={`h-4 w-4 ${isActive ? "text-primary" : "text-muted-foreground"}`}
                      />
                      <span
                        className={`text-xs font-bold ${
                          isActive ? "text-foreground" : "text-muted-foreground"
                        }`}
                      >
                        {srv.tabTitle}
                      </span>
                    </div>

                    {/* 3-Second Animated Progress Timer Bar */}
                    {isActive && (
                      <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted/60 overflow-hidden">
                        <div
                          key={activeService}
                          className="h-full bg-brand rounded-full"
                          style={{
                            animation: "flitz-progress-3s 3s linear infinite",
                          }}
                        />
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* ACTIVE SERVICE SPOTLIGHT SHOWCASE CARD (AUTO ROTATES EVERY 3 SECONDS) */}
          <Reveal key={activeServiceData.id}>
            <GlassCard className="relative overflow-hidden border-primary/30 p-8 sm:p-12 shadow-elevated transition-all duration-500">
              <div className="grid gap-10 lg:grid-cols-2 items-center">
                {/* Service Info Content */}
                <div>
                  <div className="flex items-center gap-3">
                    <span className="font-display text-4xl font-black text-primary/40">
                      {activeServiceData.step}
                    </span>
                    <span
                      className={`rounded-full px-3.5 py-1 text-xs font-bold border ${activeServiceData.badgeColor}`}
                    >
                      {activeServiceData.tag}
                    </span>
                  </div>

                  <h3 className="mt-4 text-2xl font-extrabold sm:text-3xl lg:text-4xl">
                    {activeServiceData.title}
                  </h3>

                  <p className="mt-4 text-sm leading-relaxed text-muted-foreground sm:text-base">
                    {activeServiceData.description}
                  </p>

                  <div className="mt-6 space-y-3 border-t border-border/40 pt-5">
                    {activeServiceData.highlights.map((item) => (
                      <div
                        key={item}
                        className="flex items-start gap-2.5 text-xs sm:text-sm text-foreground font-medium"
                      >
                        <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-8 flex items-center gap-4">
                    <Link
                      to={activeServiceData.actionLink}
                      className="bg-brand inline-flex items-center gap-2 rounded-full px-7 py-3.5 text-xs font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.03]"
                    >
                      {activeServiceData.actionText} <ArrowRight className="h-4 w-4" />
                    </Link>

                    <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
                      <Clock
                        className="h-4 w-4 text-primary animate-spin"
                        style={{ animationDuration: "6s" }}
                      />
                      <span>3s Auto-Advancing</span>
                    </div>
                  </div>
                </div>

                {/* Interactive Visual Feature Preview Panel */}
                <div className="relative rounded-3xl overflow-hidden border border-border p-8 glass bg-card/60 shadow-md">
                  <div className="flex items-center justify-between border-b border-border/40 pb-4">
                    <div className="flex items-center gap-3">
                      <span className="bg-brand flex h-10 w-10 items-center justify-center rounded-xl text-primary-foreground shadow-glow">
                        <ActiveServiceIcon className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="text-xs font-bold uppercase tracking-wider text-foreground">
                          {activeServiceData.title}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          Flitzz Live Service Module
                        </p>
                      </div>
                    </div>
                    <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse" />
                  </div>

                  <div className="mt-6 space-y-4 text-xs">
                    <div className="rounded-2xl border border-border/60 bg-background/60 p-4">
                      <div className="flex items-center justify-between text-muted-foreground">
                        <span>Service Health</span>
                        <span className="font-semibold text-emerald-500">Active & Syncing</span>
                      </div>
                      <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full bg-brand rounded-full"
                          style={{
                            animation: "flitz-progress-3s 3s linear infinite",
                          }}
                        />
                      </div>
                    </div>

                    <div className="rounded-2xl border border-border/60 bg-background/60 p-4 space-y-2">
                      <div className="flex items-center justify-between font-bold text-foreground">
                        <span>Operational SLA Score</span>
                        <span className="text-primary">99.4% Reliability</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">
                        Real-time pipeline monitoring continuously evaluating flight parameters.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </GlassCard>
          </Reveal>
        </section>

        {/* ==========================================
            SECTION 3: AUTOMATED 5-SECOND ROTATING STAKEHOLDER SHOWCASE
            ========================================== */}
        <section className="bg-card/40 py-24 border-y border-border/50">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <Reveal>
              <div className="text-center max-w-3xl mx-auto">
                <span className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
                  Who Benefits From Flitzz
                </span>
                <h2 className="mt-3 text-3xl font-extrabold sm:text-5xl">
                  Built for Every Aviation Stakeholder
                </h2>
                <p className="mt-3 text-muted-foreground">
                  Rotates automatically every 5 seconds. Click any tab to explore stakeholder
                  impact.
                </p>
              </div>
            </Reveal>

            {/* 4 Interactive Stakeholder Tabs with 5-Second Timer Progress Bar */}
            <div className="mt-12">
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {STAKEHOLDERS.map((item, idx) => {
                  const isActive = idx === activeStakeholder;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveStakeholder(idx)}
                      className={`relative overflow-hidden rounded-2xl p-4 text-left transition-all ${
                        isActive
                          ? "glass border-primary bg-primary/10 shadow-glow"
                          : "border border-border/50 hover:bg-accent/40"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <item.icon
                          className={`h-4 w-4 ${isActive ? "text-primary" : "text-muted-foreground"}`}
                        />
                        <span
                          className={`text-xs font-bold ${
                            isActive ? "text-foreground" : "text-muted-foreground"
                          }`}
                        >
                          {item.tabLabel}
                        </span>
                      </div>

                      {/* 5-Second Automated Progress Bar Indicator */}
                      {isActive && (
                        <div className="absolute bottom-0 left-0 right-0 h-1 bg-muted/60 overflow-hidden">
                          <div
                            key={activeStakeholder}
                            className="h-full bg-brand rounded-full"
                            style={{
                              animation: "flitz-progress 5s linear infinite",
                            }}
                          />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Active Stakeholder Professional Hero Showcase Card */}
              <Reveal key={activeStakeholderData.id} className="mt-8">
                <GlassCard className="relative overflow-hidden border-primary/30 p-8 sm:p-10 shadow-elevated">
                  <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] items-center">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="bg-brand flex h-10 w-10 items-center justify-center rounded-xl text-primary-foreground shadow-glow">
                          <StakeholderIcon className="h-5 w-5" />
                        </span>
                        <div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                            {activeStakeholderData.roleBadge}
                          </span>
                          <h3 className="text-2xl font-extrabold sm:text-3xl">
                            {activeStakeholderData.name}
                          </h3>
                        </div>
                      </div>

                      <h4 className="mt-6 text-xl font-bold text-foreground">
                        {activeStakeholderData.headline}
                      </h4>
                      <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                        {activeStakeholderData.description}
                      </p>

                      <div className="mt-6 space-y-2.5 border-t border-border/40 pt-5">
                        {activeStakeholderData.keyPoints.map((point) => (
                          <div
                            key={point}
                            className="flex items-start gap-2.5 text-xs text-foreground font-medium"
                          >
                            <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                            <span>{point}</span>
                          </div>
                        ))}
                      </div>

                      <div className="mt-8 flex flex-wrap items-center gap-4">
                        <Link
                          to={activeStakeholderData.actionLink}
                          className="bg-brand inline-flex items-center gap-2 rounded-full px-6 py-3 text-xs font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.03]"
                        >
                          {activeStakeholderData.actionText} <ArrowRight className="h-4 w-4" />
                        </Link>
                        <span className="rounded-full bg-emerald-500/10 px-4 py-2 text-xs font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                          {activeStakeholderData.stat}
                        </span>
                      </div>
                    </div>

                    {/* Preview Image Visual */}
                    <div className="relative overflow-hidden rounded-3xl border border-border shadow-md h-[280px] sm:h-[340px]">
                      <img
                        src={activeStakeholderData.heroImage}
                        alt={activeStakeholderData.name}
                        className="h-full w-full object-cover transition-transform duration-700 hover:scale-105"
                      />
                      <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-background/20 to-transparent" />
                      <div className="absolute bottom-4 left-4 right-4 rounded-2xl glass p-4">
                        <p className="text-xs font-bold text-foreground">
                          {activeStakeholderData.stat}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          {activeStakeholderData.statSub}
                        </p>
                      </div>
                    </div>
                  </div>
                </GlassCard>
              </Reveal>
            </div>
          </div>
        </section>

        {/* ==========================================
            SECTION 4: INTERACTIVE GLOBAL NETWORK MAP
            ========================================== */}
        <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6">
          <Reveal>
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-widest text-primary">
                  Geospatial Air Network Radar
                </span>
                <h2 className="text-3xl font-extrabold sm:text-4xl">
                  Global Air Network Risk Radar
                </h2>
              </div>
              <div className="flex items-center gap-3 text-xs font-medium text-muted-foreground">
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: "var(--risk-low)" }}
                  />
                  🟢 Green (&lt;50%)
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: "var(--risk-medium)" }}
                  />
                  🟡 Yellow (50–75%)
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: "var(--risk-high)" }}
                  />
                  🔴 Red (&gt;75%)
                </span>
              </div>
            </div>

            <FlightMap routes={MAP_ROUTES} height={480} showLegend={true} animate={true} />
          </Reveal>
        </section>

        {/* ==========================================
            SECTION 5: CONTACT US & ENTERPRISE INQUIRY
            ========================================== */}
        <section className="bg-card/40 py-24 border-t border-border/50">
          <div className="mx-auto max-w-7xl px-4 sm:px-6">
            <Reveal>
              <div className="text-center max-w-3xl mx-auto mb-16">
                <span className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
                  Get In Touch
                </span>
                <h2 className="mt-3 text-3xl font-extrabold sm:text-5xl">
                  Contact Flitzz Operations Team
                </h2>
                <p className="mt-3 text-muted-foreground text-base">
                  Have questions about integrating predictive LightGBM APIs, airline fleet setup, or
                  passenger rebooking channels? Our 24/7 aviation command team is ready to assist.
                </p>
              </div>
            </Reveal>

            <div className="grid gap-8 lg:grid-cols-2">
              {/* Left Column: Direct Contact Info Cards */}
              <Reveal delay={100}>
                <div className="space-y-4">
                  <GlassCard className="flex items-start gap-4 p-6 border-border/60">
                    <span className="bg-brand flex h-12 w-12 items-center justify-center rounded-2xl text-primary-foreground shadow-glow flex-shrink-0">
                      <Mail className="h-6 w-6" />
                    </span>
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                        Official Support Email
                      </span>
                      <h3 className="mt-1 text-lg font-bold text-foreground">
                        <a href="mailto:contact@flitzz.ai" className="hover:underline">
                          contact@flitzz.ai
                        </a>
                      </h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        For general inquiries, dispatcher API keys, and partner carrier support.
                      </p>
                    </div>
                  </GlassCard>

                  <GlassCard className="flex items-start gap-4 p-6 border-border/60">
                    <span className="bg-brand flex h-12 w-12 items-center justify-center rounded-2xl text-primary-foreground shadow-glow flex-shrink-0">
                      <Clock className="h-6 w-6" />
                    </span>
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                        24/7 Operations Hotline
                      </span>
                      <h3 className="mt-1 text-lg font-bold text-foreground">
                        <a href="tel:+180055535489" className="hover:underline">
                          +1 (800) 555-FLITZ (+1 800-555-35489)
                        </a>
                      </h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Immediate 24/7 priority line for active flight dispatchers & ground
                        controllers.
                      </p>
                    </div>
                  </GlassCard>

                  <GlassCard className="flex items-start gap-4 p-6 border-border/60">
                    <span className="bg-brand flex h-12 w-12 items-center justify-center rounded-2xl text-primary-foreground shadow-glow flex-shrink-0">
                      <Globe className="h-6 w-6" />
                    </span>
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                        Global Aviation Headquarters
                      </span>
                      <h3 className="mt-1 text-lg font-bold text-foreground">
                        San Francisco, California
                      </h3>
                      <p className="mt-1 text-xs text-muted-foreground">
                        100 Aviation Plaza, Suite 400, San Francisco International Airport, CA 94128
                      </p>
                    </div>
                  </GlassCard>
                </div>
              </Reveal>

              {/* Right Column: Interactive Glass Contact Form */}
              <Reveal delay={200}>
                <GlassCard className="p-8 border-primary/30 shadow-elevated">
                  <h3 className="text-xl font-bold text-foreground">Send Us a Direct Message</h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Fill out your contact details below and our team will get back to you in &lt;15
                    mins.
                  </p>

                  {contactSubmitted ? (
                    <div className="mt-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 p-6 text-center">
                      <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500 mb-3" />
                      <h4 className="text-lg font-bold text-foreground">
                        Thank You! Message Received.
                      </h4>
                      <p className="mt-2 text-xs text-muted-foreground">
                        Our operational dispatch team has received your message at{" "}
                        <strong className="text-foreground">contact@flitzz.ai</strong> and will
                        respond shortly.
                      </p>
                    </div>
                  ) : (
                    <form onSubmit={handleContactSubmit} className="mt-6 space-y-4">
                      <div className="grid gap-4 sm:grid-cols-2">
                        <div>
                          <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                            Full Name *
                          </label>
                          <input
                            type="text"
                            required
                            value={contactForm.name}
                            onChange={(e) =>
                              setContactForm({ ...contactForm, name: e.target.value })
                            }
                            placeholder="Captain Sarah Miller"
                            className="w-full rounded-xl border border-input bg-background/70 py-2.5 px-3.5 text-xs outline-none transition-shadow focus:border-primary focus:shadow-glow"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                            Work Email *
                          </label>
                          <input
                            type="email"
                            required
                            value={contactForm.email}
                            onChange={(e) =>
                              setContactForm({ ...contactForm, email: e.target.value })
                            }
                            placeholder="sarah@airline.com"
                            className="w-full rounded-xl border border-input bg-background/70 py-2.5 px-3.5 text-xs outline-none transition-shadow focus:border-primary focus:shadow-glow"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                          Airline / Organization Name
                        </label>
                        <input
                          type="text"
                          value={contactForm.org}
                          onChange={(e) => setContactForm({ ...contactForm, org: e.target.value })}
                          placeholder="Global Airways Dispatch Control"
                          className="w-full rounded-xl border border-input bg-background/70 py-2.5 px-3.5 text-xs outline-none transition-shadow focus:border-primary focus:shadow-glow"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                          Message / Inquiry Details *
                        </label>
                        <textarea
                          required
                          rows={4}
                          value={contactForm.message}
                          onChange={(e) =>
                            setContactForm({ ...contactForm, message: e.target.value })
                          }
                          placeholder="How can Flitzz assist your airline operations, crew scheduling, or passenger rebooking?"
                          className="w-full rounded-xl border border-input bg-background/70 p-3 text-xs outline-none transition-shadow focus:border-primary focus:shadow-glow resize-none"
                        />
                      </div>

                      <button
                        type="submit"
                        className="bg-brand w-full inline-flex items-center justify-center gap-2 rounded-full py-3.5 text-xs font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.02]"
                      >
                        Send Message to Flitzz Operations <ArrowRight className="h-4 w-4" />
                      </button>
                    </form>
                  )}
                </GlassCard>
              </Reveal>
            </div>
          </div>
        </section>

        {/* ==========================================
            SECTION 6: BOTTOM-CENTERED MOTIVATIONAL QUOTE
            ========================================== */}
        <section className="mx-auto max-w-5xl px-4 py-20">
          <Reveal>
            <div className="glass relative overflow-hidden rounded-[2.5rem] p-10 text-center shadow-glow border-primary/30">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand text-primary-foreground shadow-glow mb-6">
                <Quote className="h-7 w-7" />
              </div>

              <blockquote className="font-display text-2xl font-extrabold leading-relaxed sm:text-3xl lg:text-4xl text-foreground max-w-3xl mx-auto">
                "Delay is inevitable in aviation; remaining unprepared is a choice. Flitzz turns
                atmospheric uncertainty into absolute operational precision."
              </blockquote>

              <div className="mt-6 flex items-center justify-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  Flitzz Operational Principle
                </span>
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              </div>
            </div>
          </Reveal>
        </section>

        <SiteFooter />
      </div>
    </>
  );
}