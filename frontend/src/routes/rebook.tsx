import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Compass,
  CreditCard,
  Check,
  Mail,
  Plane,
  RefreshCw,
  Send,
  ShieldCheck,
  Sparkles,
  Ticket,
  User,
  Coffee,
} from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";

import { TEAMMATE_PRESETS, type DemoTeammate, type PassengerEmailPayload, type EmailDispatchLog } from "@/lib/email-types";
import { buildEmailPayload, evaluateEmailTriggerRule, calculateRiskScore } from "@/services/emailTriggerService";
import { EmailPreviewModal } from "@/components/email-preview-modal";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

import { FlightIcon } from "@/components/flight-icon";
import { GlassCard, PageShell, Reveal, RiskBadge } from "@/components/flitz-ui";
import { AIRPORTS, airport, riskToken, type RiskLevel } from "@/lib/flitz-data";

export const Route = createFileRoute("/rebook")({
  head: () => ({
    meta: [
      { title: "AI Rebooking & Passenger Notification — FLITZZZZ" },
      {
        name: "description",
        content:
          "Find alternate flight recommendations, issue instant rebooking passes, and trigger delay notification emails to passengers.",
      },
    ],
  }),
  component: RebookPage,
});

type DelayedFlight = {
  id: string;
  flightNo: string;
  airline: string;
  origin: string;
  destination: string;
  scheduledDep: string;
  delayMin: number;
  riskLevel: RiskLevel;
  passengersCount: number;
  reason: string;
};

const DELAYED_FLIGHTS: DelayedFlight[] = [
  {
    id: "f-101",
    flightNo: "DL1492",
    airline: "Delta Air Lines",
    origin: "JFK",
    destination: "LHR",
    scheduledDep: "18:35",
    delayMin: 85,
    riskLevel: "High",
    passengersCount: 284,
    reason: "Convective Weather & Runway Congestion at JFK",
  },
  {
    id: "f-102",
    flightNo: "UA890",
    airline: "United Airlines",
    origin: "ORD",
    destination: "SFO",
    scheduledDep: "14:15",
    delayMin: 60,
    riskLevel: "High",
    passengersCount: 210,
    reason: "Ground Stop & Sector Air Traffic Restriction",
  },
  {
    id: "f-103",
    flightNo: "BA117",
    airline: "British Airways",
    origin: "LHR",
    destination: "JFK",
    scheduledDep: "09:40",
    delayMin: 110,
    riskLevel: "High",
    passengersCount: 312,
    reason: "Inbound Aircraft Maintenance Swap",
  },
  {
    id: "f-104",
    flightNo: "AA204",
    airline: "American Airlines",
    origin: "DFW",
    destination: "LAX",
    scheduledDep: "16:50",
    delayMin: 45,
    riskLevel: "Medium",
    passengersCount: 178,
    reason: "Crew Rotation Duty Limit Delay",
  },
];

type AlternateOption = {
  id: string;
  flightNo: string;
  airline: string;
  departure: string;
  arrival: string;
  duration: string;
  seatsAvailable: number;
  matchScore: number;
  timeSavedMin: number;
  type: "Direct" | "Connecting";
  stops?: string;
  perks: string[];
};

type Passenger = {
  name: string;
  email: string;
  pnr: string;
  seat: string;
  class: string;
};

const SAMPLE_PASSENGERS: Record<string, Passenger[]> = {
  "f-101": [
    {
      name: "Sophia Martinez",
      email: "sophia.m@aviation-corp.com",
      pnr: "FL88392",
      seat: "04A",
      class: "Business Class",
    },
    {
      name: "Marcus Vance",
      email: "marcus.vance@techfleet.io",
      pnr: "FL99420",
      seat: "14C",
      class: "Premium Economy",
    },
    {
      name: "Elena Rostova",
      email: "elena.r@globalpass.org",
      pnr: "FL30219",
      seat: "22F",
      class: "Economy",
    },
  ],
  "f-102": [
    {
      name: "David Chen",
      email: "david.chen@enterprise.com",
      pnr: "UA44120",
      seat: "02B",
      class: "First Class",
    },
    {
      name: "Amara Okezie",
      email: "amara.o@designlabs.co",
      pnr: "UA99104",
      seat: "11D",
      class: "Economy",
    },
  ],
  "f-103": [
    {
      name: "Oliver Smith",
      email: "oliver.smith@uktravel.co.uk",
      pnr: "BA11093",
      seat: "06K",
      class: "Club World",
    },
  ],
  "f-104": [
    {
      name: "Rachel Green",
      email: "rachel.g@fashionhq.com",
      pnr: "AA77301",
      seat: "08A",
      class: "Main Cabin",
    },
  ],
};

export function RebookPage() {
  const [selectedFlightId, setSelectedFlightId] = useState<string>("f-101");
  const [selectedPassengerIdx, setSelectedPassengerIdx] = useState<number>(0);
  const [rebookedId, setRebookedId] = useState<string | null>(null);
  
  // Email Simulator State
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchProgress, setDispatchProgress] = useState(0);
  const [emailLogs, setEmailLogs] = useState<EmailDispatchLog[]>([]);
  const [previewPayload, setPreviewPayload] = useState<PassengerEmailPayload | null>(null);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const activeFlight =
    DELAYED_FLIGHTS.find((f) => f.id === selectedFlightId) ?? DELAYED_FLIGHTS[0]!;
  // Inject demo teammates into the passengers list
  const basePassengers = SAMPLE_PASSENGERS[activeFlight.id] ?? SAMPLE_PASSENGERS["f-101"]!;
  const mappedTeammates = TEAMMATE_PRESETS.map((tm, i) => ({
    name: tm.name,
    email: tm.email,
    pnr: `TM${10000 + i}`,
    seat: tm.seat,
    class: tm.class
  }));
  const passengers = [...mappedTeammates, ...basePassengers];
  
  const activePassenger = passengers[selectedPassengerIdx] ?? passengers[0]!;
  
  const currentRiskScore = calculateRiskScore(activeFlight.delayMin);
  const triggerRule = evaluateEmailTriggerRule(currentRiskScore);

  const org = airport(activeFlight.origin);
  const dst = airport(activeFlight.destination);

  const ALTERNATES: AlternateOption[] = [
    {
      id: "alt-1",
      flightNo: "VS004",
      airline: "Virgin Atlantic",
      departure: "19:10",
      arrival: "07:15 (+1d)",
      duration: "7h 05m",
      seatsAvailable: 12,
      matchScore: 99,
      timeSavedMin: 70,
      type: "Direct",
      perks: ["Complimentary Lounge Access", "Automatic Baggage Transfer", "Priority Check-in"],
    },
    {
      id: "alt-2",
      flightNo: "BA178",
      airline: "British Airways",
      departure: "19:55",
      arrival: "07:50 (+1d)",
      duration: "6h 55m",
      seatsAvailable: 8,
      matchScore: 94,
      timeSavedMin: 45,
      type: "Direct",
      perks: ["Fast-Track Security Pass", "$50 Inflight Voucher", "Free Seat Selection"],
    },
    {
      id: "alt-3",
      flightNo: "AF007 + AF1680",
      airline: "Air France via CDG",
      departure: "18:45",
      arrival: "09:10 (+1d)",
      duration: "9h 25m",
      seatsAvailable: 18,
      matchScore: 86,
      timeSavedMin: 20,
      type: "Connecting",
      stops: "1 stop (CDG 1h 20m)",
      perks: ["Hotel Transfer Guarantee", "Double Frequent Flyer Miles"],
    },
  ];

  function handleRebook(option: AlternateOption) {
    setRebookedId(option.id);
    toast.success(`Successfully rebooked ${activePassenger.name} on ${option.flightNo}!`, {
      description: `New departure at ${option.departure} (${option.airline}). Time saved: ${option.timeSavedMin} mins.`,
    });
  }

  function handleSimulateBatchDispatch() {
    setIsDispatching(true);
    setDispatchProgress(0);
    
    // Simulate sending to all passengers in the list
    let currentIdx = 0;
    const interval = setInterval(() => {
      if (currentIdx >= passengers.length) {
        clearInterval(interval);
        setIsDispatching(false);
        toast.success(`Batch Dispatch Complete`, {
          description: `Successfully evaluated and triggered emails for ${passengers.length} passengers.`,
        });
        return;
      }
      
      const p = passengers[currentIdx];
      const payload = buildEmailPayload(
        p.name, p.email, p.pnr, p.seat, p.class,
        activeFlight.id, activeFlight.flightNo,
        org.name, dst.name, activeFlight.scheduledDep,
        activeFlight.delayMin, activeFlight.reason
      );
      
      const newLog: EmailDispatchLog = {
        id: `msg-${Date.now()}-${currentIdx}`,
        passenger: p.name,
        flight: activeFlight.flightNo,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        tier: payload.tier,
        status: "Sent"
      };
      
      setEmailLogs((prev) => [newLog, ...prev]);
      setDispatchProgress(((currentIdx + 1) / passengers.length) * 100);
      currentIdx++;
    }, 400); // 400ms per passenger
  }
  
  function handlePreviewEmail(p = activePassenger) {
    const payload = buildEmailPayload(
      p.name, p.email, p.pnr, p.seat, p.class,
      activeFlight.id, activeFlight.flightNo,
      org.name, dst.name, activeFlight.scheduledDep,
      activeFlight.delayMin, activeFlight.reason
    );
    setPreviewPayload(payload);
    setIsPreviewOpen(true);
  }

  return (
    <PageShell
      eyebrow="Smart Disruption Recovery"
      title="AI Flight Rebooking & Passenger Alerts"
      description="Find instant alternate connections for delayed flights, issue digital rebooking passes, and trigger real-time delay notifications to passengers."
    >
      <div className="grid gap-6 lg:grid-cols-[380px_1fr]">
        {/* Left Column: Delayed Flight & Passenger Selector */}
        <div className="grid gap-6">
          <Reveal>
            <GlassCard>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                <AlertTriangle className="h-4 w-4" /> Disrupted Flight Selector
              </div>
              <h2 className="mt-2 text-xl font-bold">Select Delayed Flight</h2>
              <div className="mt-4 grid gap-3">
                {DELAYED_FLIGHTS.map((f) => {
                  const selected = f.id === selectedFlightId;
                  return (
                    <button
                      key={f.id}
                      onClick={() => {
                        setSelectedFlightId(f.id);
                        setSelectedPassengerIdx(0);
                        setRebookedId(null);
                      }}
                      className={`w-full rounded-2xl border p-4 text-left transition-all ${
                        selected
                          ? "border-primary bg-primary/10 shadow-glow"
                          : "border-border hover:bg-accent/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-display font-extrabold text-foreground">
                          {f.flightNo} · {f.airline}
                        </span>
                        <RiskBadge level={f.riskLevel} />
                      </div>
                      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                        <span>
                          {f.origin} → {f.destination} ({f.scheduledDep})
                        </span>
                        <span className="font-semibold text-destructive">
                          +{f.delayMin} min delay
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </GlassCard>
          </Reveal>

          <Reveal delay={80}>
            <GlassCard>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                <User className="h-4 w-4" /> Passenger Profile
              </div>
              <h2 className="mt-2 text-xl font-bold">Impacted Passengers</h2>
              <div className="mt-4 grid gap-2">
                {passengers.map((p, idx) => {
                  const active = idx === selectedPassengerIdx;
                  return (
                    <button
                      key={p.pnr}
                      onClick={() => {
                        setSelectedPassengerIdx(idx);
                        setRebookedId(null);
                      }}
                      className={`flex items-center justify-between rounded-xl border p-3 text-left transition-all ${
                        active
                          ? "border-primary bg-accent/60 font-semibold"
                          : "border-border hover:bg-accent/30"
                      }`}
                    >
                      <div>
                        <p className="text-sm font-medium text-foreground">{p.name}</p>
                        <p className="text-xs text-muted-foreground">
                          PNR: {p.pnr} · Seat {p.seat} ({p.class})
                        </p>
                      </div>
                      {active && <CheckCircle2 className="h-4 w-4 text-primary" />}
                    </button>
                  );
                })}
              </div>
            </GlassCard>
          </Reveal>
        </div>

        {/* Right Column: AI Rebooking Engine & Email Trigger */}
        <div className="grid gap-6">
          {/* Active Flight Header Banner */}
          <Reveal delay={60}>
            <GlassCard className="relative overflow-hidden border-primary/30">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <span className="glass inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold text-destructive">
                    <Clock className="h-3.5 w-3.5" /> Delay Confirmed +{activeFlight.delayMin} mins
                  </span>
                  <h2 className="mt-3 text-2xl font-extrabold">
                    {activeFlight.flightNo}: {org.name} ({org.code}) → {dst.name} ({dst.code})
                  </h2>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Reason: {activeFlight.reason} · Affected Passenger:{" "}
                    <span className="font-semibold text-foreground">{activePassenger.name}</span> (
                    {activePassenger.class})
                  </p>
                </div>
                <div className="flex flex-col gap-2 items-end">
                  <Badge variant="outline" className={`
                    ${triggerRule.tier === 'Critical' ? 'border-red-500/50 bg-red-500/10 text-red-400' : ''}
                    ${triggerRule.tier === 'Warning' ? 'border-orange-500/50 bg-orange-500/10 text-orange-400' : ''}
                    ${triggerRule.tier === 'Monitoring' ? 'border-amber-500/50 bg-amber-500/10 text-amber-400' : ''}
                    ${triggerRule.tier === 'Optimal' ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400' : ''}
                  `}>
                    Trigger Rule: {triggerRule.tier} ({currentRiskScore} Risk)
                  </Badge>
                  <button
                    onClick={handleSimulateBatchDispatch}
                    disabled={isDispatching}
                    className="bg-brand inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.02] disabled:opacity-50"
                  >
                    {isDispatching ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    {isDispatching ? "Dispatching..." : "Simulate Batch Dispatch"}
                  </button>
                </div>
              </div>
            </GlassCard>
          </Reveal>

          {isDispatching && (
            <Reveal delay={80}>
              <GlassCard className="border-brand/40 bg-brand/5">
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-semibold text-brand">Automated Email Dispatch in Progress</span>
                  <span className="text-muted-foreground">{Math.round(dispatchProgress)}%</span>
                </div>
                <Progress value={dispatchProgress} className="h-2" />
                <p className="text-xs text-muted-foreground mt-2">
                  Evaluating trigger rules and generating tailored HTML templates for {passengers.length} passengers...
                </p>
              </GlassCard>
            </Reveal>
          )}

          {/* AI Rebooking Recommendations Section */}
          <Reveal delay={120}>
            <GlassCard>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
                    <Sparkles className="h-4 w-4" /> AI Engine Recommendation
                  </span>
                  <h3 className="text-xl font-bold">Optimal Alternate Flights</h3>
                </div>
                <span className="text-xs text-muted-foreground">
                  3 direct & connecting routes analyzed
                </span>
              </div>

              <div className="mt-5 grid gap-4">
                {ALTERNATES.map((alt) => {
                  const isRebooked = rebookedId === alt.id;
                  return (
                    <div
                      key={alt.id}
                      className={`relative rounded-2xl border p-5 transition-all ${
                        isRebooked
                          ? "border-emerald-500/60 bg-emerald-500/10 shadow-glow"
                          : "border-border hover:border-primary/40 hover:bg-accent/20"
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div className="flex items-center gap-3">
                          <span className="bg-brand flex h-10 w-10 items-center justify-center rounded-xl text-primary-foreground shadow-glow">
                            <FlightIcon className="h-5 w-5" />
                          </span>
                          <div>
                            <div className="flex items-center gap-2">
                              <h4 className="text-lg font-bold">{alt.flightNo}</h4>
                              <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-semibold text-primary">
                                {alt.airline}
                              </span>
                              <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                                {alt.matchScore}% AI Match
                              </span>
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                              Departs {alt.departure} → Arrives {alt.arrival} ({alt.duration}) ·{" "}
                              {alt.type} {alt.stops ? `· ${alt.stops}` : ""}
                            </p>
                          </div>
                        </div>

                        <div className="text-right">
                          <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                            Saves {alt.timeSavedMin} mins
                          </span>
                          <p className="text-xs text-muted-foreground">
                            {alt.seatsAvailable} seats left in {activePassenger.class}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border/50 pt-3">
                        <div className="flex flex-wrap items-center gap-2">
                          {alt.perks.map((perk) => (
                            <span
                              key={perk}
                              className="inline-flex items-center gap-1 rounded-md bg-accent/60 px-2.5 py-1 text-xs font-medium text-foreground"
                            >
                              <ShieldCheck className="h-3 w-3 text-primary" /> {perk}
                            </span>
                          ))}
                        </div>

                        <button
                          onClick={() => handleRebook(alt)}
                          disabled={isRebooked}
                          className={`inline-flex items-center gap-2 rounded-full px-5 py-2 text-xs font-semibold transition-all ${
                            isRebooked
                              ? "bg-emerald-600 text-white"
                              : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow"
                          }`}
                        >
                          {isRebooked ? (
                            <>
                              <Check className="h-3.5 w-3.5" /> Pass Issued & Rebooked
                            </>
                          ) : (
                            <>
                              <Ticket className="h-3.5 w-3.5" /> Rebook & Issue Pass
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </GlassCard>
          </Reveal>

          {/* Passenger Email Notification Live Preview Card */}
          <Reveal delay={180}>
            <GlassCard>
              <div className="flex items-center justify-between border-b border-border/50 pb-4">
                <div className="flex items-center gap-2">
                  <Mail className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-bold">FlightGuard AI Email Triggers</h3>
                </div>
                <button
                  onClick={() => handlePreviewEmail(activePassenger)}
                  className="rounded-full bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary transition-colors hover:bg-primary/20 flex items-center gap-1.5"
                >
                  <Mail className="h-3.5 w-3.5" /> Preview Template
                </button>
              </div>

              <div className="mt-4 rounded-2xl border border-border bg-background/80 p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/40 pb-3 text-xs text-muted-foreground">
                  <p>
                    <span className="font-semibold text-foreground">To:</span>{" "}
                    {activePassenger.name} &lt;{activePassenger.email}&gt;
                  </p>
                  <p>
                    <span className="font-semibold text-foreground">Subject:</span> Important
                    Update: Your flight {activeFlight.flightNo} delay & rebooking options
                  </p>
                </div>

                <div className="mt-4 space-y-3 text-xs leading-relaxed text-foreground">
                  <p className="font-semibold">Dear {activePassenger.name},</p>
                  <p>
                    We regret to inform you that your upcoming flight{" "}
                    <strong className="text-primary">{activeFlight.flightNo}</strong> from{" "}
                    <strong>{activeFlight.origin}</strong> to{" "}
                    <strong>{activeFlight.destination}</strong> scheduled for departure at{" "}
                    {activeFlight.scheduledDep} has been delayed by approximately{" "}
                    <strong className="text-destructive">{activeFlight.delayMin} minutes</strong>{" "}
                    due to {activeFlight.reason}.
                  </p>

                  <div className="rounded-xl border border-primary/30 bg-primary/5 p-3.5">
                    <p className="font-semibold text-primary">
                      Your Automated Recovery Options & Voucher:
                    </p>
                    <ul className="mt-2 list-inside list-disc space-y-1 text-muted-foreground">
                      <li>
                        Complimentary $45 Executive Airport Lounge & Refreshment Voucher (Code:{" "}
                        <strong className="text-foreground">
                          FLITZ-VOUCHER-{activePassenger.pnr}
                        </strong>
                        )
                      </li>
                      <li>
                        Instant 1-Click Alternate Flight Rebooking Portal with guaranteed seat
                        protection
                      </li>
                      <li>Free Priority Baggage Transfer across all partner airlines</li>
                    </ul>
                  </div>

                  <p>
                    You can view live route updates and select your preferred alternate flight at:{" "}
                    <span className="underline text-primary font-medium">
                      https://flightwise-ai.com/rebook?pnr={activePassenger.pnr}
                    </span>
                  </p>
                  <p className="pt-2 text-muted-foreground">
                    Sincerely,
                    <br />
                    <strong className="text-foreground">FlightWise AI Operations Center</strong>
                  </p>
                </div>
              </div>

              {emailLogs.length > 0 && (
                <div className="mt-5 border-t border-border/50 pt-4">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Recent Trigger Log
                  </p>
                  <div className="grid gap-1.5">
                    {emailLogs.map((log) => (
                      <div
                        key={log.id}
                        className="flex items-center justify-between text-xs rounded-lg bg-accent/40 px-3 py-1.5"
                      >
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={`text-[10px] py-0 h-4 
                            ${log.tier === 'Critical' ? 'border-red-500 text-red-500' : ''}
                            ${log.tier === 'Warning' ? 'border-orange-500 text-orange-500' : ''}
                            ${log.tier === 'Monitoring' ? 'border-amber-500 text-amber-500' : ''}
                            ${log.tier === 'Optimal' ? 'border-emerald-500 text-emerald-500' : ''}
                          `}>
                            {log.tier}
                          </Badge>
                          <span className="text-foreground">
                            Alert sent to <strong>{log.passenger}</strong> for flight {log.flight}
                          </span>
                        </div>
                        <span className="text-muted-foreground">{log.timestamp}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </GlassCard>
          </Reveal>
        </div>
      </div>
      <EmailPreviewModal 
        isOpen={isPreviewOpen} 
        onOpenChange={setIsPreviewOpen} 
        payload={previewPayload} 
      />
    </PageShell>
  );
}
