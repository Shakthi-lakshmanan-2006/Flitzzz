import { createFileRoute } from "@tanstack/react-router";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Cpu,
  Layers,
  Plane,
  RefreshCw,
  ShieldAlert,
  Sliders,
  UserCheck,
  Users,
  Wrench,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { FlightIcon } from "@/components/flight-icon";
import { GlassCard, PageShell, Reveal, RiskBadge } from "@/components/flitz-ui";

export const Route = createFileRoute("/ops")({
  head: () => ({
    meta: [
      { title: "Airline Operations Dashboard & Crew Scheduling — FLITZZZZ" },
      {
        name: "description",
        content:
          "Operational intelligence dashboard for airline managers: crew scheduling, duty hour tracking, turnaround timers, and aircraft gate assignments.",
      },
    ],
  }),
  component: OpsManagerPage,
});

type CrewMember = {
  id: string;
  crewId?: number;
  name: string;
  role: "Captain" | "First Officer" | "Lead Attendant" | "Cabin Crew";
  flightNo: string;
  dutyRemaining: string;
  dutyLimitWarning?: boolean;
  status: "Assigned" | "Standby" | "Off Duty";
};

type AircraftTurnaround = {
  id: string;
  tailNumber: string;
  model: string;
  flightNo: string;
  gate: string;
  nextGate?: string;
  fuelingPct: number;
  cateringPct: number;
  baggagePct: number;
  cleaningPct: number;
  turnaroundEstMin: number;
};

const INITIAL_CREW: CrewMember[] = [
  {
    id: "c-1",
    name: "Capt. Alexander Vance",
    role: "Captain",
    flightNo: "DL1492",
    dutyRemaining: "2h 45m",
    dutyLimitWarning: true,
    status: "Assigned",
  },
  {
    id: "c-2",
    name: "F/O Sarah Jenkins",
    role: "First Officer",
    flightNo: "DL1492",
    dutyRemaining: "6h 10m",
    status: "Assigned",
  },
  {
    id: "c-3",
    name: "Capt. Michael Thorne (Standby)",
    role: "Captain",
    flightNo: "Standby Pool",
    dutyRemaining: "9h 30m",
    status: "Standby",
  },
  {
    id: "c-4",
    name: "Capt. Robert Sterling",
    role: "Captain",
    flightNo: "UA890",
    dutyRemaining: "7h 15m",
    status: "Assigned",
  },
  {
    id: "c-5",
    name: "Lead Flight Att. Chloe Bennett",
    role: "Lead Attendant",
    flightNo: "BA117",
    dutyRemaining: "5h 20m",
    status: "Assigned",
  },
];

const INITIAL_TURNAROUND: AircraftTurnaround[] = [
  {
    id: "ac-1",
    tailNumber: "N802DL",
    model: "Boeing 787-9",
    flightNo: "DL1492",
    gate: "Gate B12",
    fuelingPct: 90,
    cateringPct: 100,
    baggagePct: 75,
    cleaningPct: 100,
    turnaroundEstMin: 18,
  },
  {
    id: "ac-2",
    tailNumber: "N491UA",
    model: "Airbus A350-900",
    flightNo: "UA890",
    gate: "Gate C04",
    fuelingPct: 60,
    cateringPct: 80,
    baggagePct: 40,
    cleaningPct: 90,
    turnaroundEstMin: 32,
  },
  {
    id: "ac-3",
    tailNumber: "N704BA",
    model: "Boeing 777-300ER",
    flightNo: "BA117",
    gate: "Gate A08",
    fuelingPct: 100,
    cateringPct: 100,
    baggagePct: 95,
    cleaningPct: 100,
    turnaroundEstMin: 8,
  },
];

export function OpsManagerPage() {
  const [crewList, setCrewList] = useState<CrewMember[]>(INITIAL_CREW);
  const [turnaroundList, setTurnaroundList] = useState<AircraftTurnaround[]>(INITIAL_TURNAROUND);
  const [dispatching, setDispatching] = useState(false);
  const [crewFlightId, setCrewFlightId] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/api/crew")
      .then((response) => response.json())
      .then((members) => {
        setCrewList(
          (members as Array<Record<string, unknown>>).map((member) => ({
            id: String(member.crew_id),
            crewId: Number(member.crew_id),
            name: `${member.first_name} ${member.last_name}`,
            role: member.role === "CAPTAIN"
              ? "Captain"
              : member.role === "FIRST_OFFICER"
                ? "First Officer"
                : "Cabin Crew",
            flightNo: "Available",
            dutyRemaining: "Available",
            status: member.status === "ACTIVE" ? "Standby" : "Off Duty",
          })),
        );
      })
      .catch(() => toast.error("Unable to load crew members from PostgreSQL."));
  }, []);

  async function assignCrewMember(crew: CrewMember) {
    const flightId = Number(crewFlightId);
    if (!crew.crewId || !Number.isInteger(flightId) || flightId <= 0) {
      toast.error("Enter a valid flight ID before assigning crew.");
      return;
    }

    const response = await fetch("http://localhost:8000/api/crew-assignments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        flight_id: flightId,
        assignments: [{ crew_id: crew.crewId, assignment_role: crew.role }],
      }),
    });

    const body = await response.json();
    if (!response.ok) {
      toast.error(body.detail || "Crew assignment failed.");
      return;
    }

    setCrewList((current) => current.map((member) =>
      member.id === crew.id ? { ...member, flightNo: `Flight ${flightId}`, status: "Assigned" } : member,
    ));
    toast.success(`${crew.name} assigned to flight ${flightId}.`);
  }

  function handleCrewSwap(targetId: string) {
    setCrewList((prev) =>
      prev.map((c) => {
        if (c.id === targetId) {
          return {
            ...c,
            name: "Capt. Michael Thorne (Reassigned)",
            dutyRemaining: "9h 30m",
            dutyLimitWarning: false,
          };
        }
        return c;
      }),
    );
    toast.success("Standby Crew Reassigned!", {
      description: "Capt. Michael Thorne assigned to DL1492. Duty limit risk resolved.",
    });
  }

  function handleFastTrackTurnaround(aircraftId: string) {
    setTurnaroundList((prev) =>
      prev.map((ac) => {
        if (ac.id === aircraftId) {
          return {
            ...ac,
            fuelingPct: 100,
            cateringPct: 100,
            baggagePct: 100,
            cleaningPct: 100,
            turnaroundEstMin: 0,
          };
        }
        return ac;
      }),
    );
    toast.success("Turnaround Fast-Tracked!", {
      description: "Priority ground crew dispatched. Ground handling completed 100%.",
    });
  }

  function handleTriggerEmergencyDispatch() {
    setDispatching(true);
    setTimeout(() => {
      setDispatching(false);
      toast.success("Relief Aircraft Dispatched from Hangar", {
        description: "Boeing 787-9 (Tail N910DL) assigned to relieve delayed slot.",
      });
    }, 1000);
  }

  return (
    <PageShell
      eyebrow="Airline Operations Center"
      title="Manager Operations & Crew Control"
      description="Real-time operational dashboard for flight managers: monitor turnaround times, crew duty hour limits, aircraft gate assignments, and ground dispatch mitigations."
    >
      {/* Top Manager KPI Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Reveal delay={40}>
          <GlassCard>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Active Fleet Status
              </span>
              <Plane className="h-4 w-4 text-primary" />
            </div>
            <p className="font-display mt-3 text-3xl font-extrabold">142 Aircraft</p>
            <p className="mt-1 text-xs text-emerald-600 dark:text-emerald-400">
              88 Airborne · 14 Turnaround · 2 Hangar
            </p>
          </GlassCard>
        </Reveal>

        <Reveal delay={80}>
          <GlassCard>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Crew Duty Health
              </span>
              <UserCheck className="h-4 w-4 text-primary" />
            </div>
            <p className="font-display mt-3 text-3xl font-extrabold">96.8% Compliant</p>
            <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
              1 Captain nearing FAA duty limit
            </p>
          </GlassCard>
        </Reveal>

        <Reveal delay={120}>
          <GlassCard>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Turnaround Index
              </span>
              <Activity className="h-4 w-4 text-primary" />
            </div>
            <p className="font-display mt-3 text-3xl font-extrabold">18.4 min avg</p>
            <p className="mt-1 text-xs text-emerald-600 dark:text-emerald-400">
              -4.2 min faster than target
            </p>
          </GlassCard>
        </Reveal>

        <Reveal delay={160}>
          <GlassCard>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Disruption Mitigation
              </span>
              <Zap className="h-4 w-4 text-primary" />
            </div>
            <p className="font-display mt-3 text-3xl font-extrabold">Auto-Active</p>
            <p className="mt-1 text-xs text-primary font-medium">3 Standby Crews Ready</p>
          </GlassCard>
        </Reveal>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        {/* Crew Scheduling & Duty Hour Tracker */}
        <Reveal delay={100}>
          <GlassCard className="h-full">
            <div className="flex items-center justify-between">
              <div>
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
                  <Users className="h-4 w-4" /> Roster Management
                </span>
                <h3 className="text-xl font-bold">Crew Duty & Flight Assignments</h3>
              </div>
              <div className="flex items-center gap-2">
                <input
                  value={crewFlightId}
                  onChange={(event) => setCrewFlightId(event.target.value.replace(/\D/g, ""))}
                  placeholder="Flight ID"
                  className="w-24 rounded-full border border-input bg-background/60 px-3 py-1.5 text-xs outline-none"
                />
                <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
                  {crewList.length} Available
                </span>
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              {crewList.map((crew) => (
                <div
                  key={crew.id}
                  className={`rounded-2xl border p-4 transition-all ${
                    crew.dutyLimitWarning
                      ? "border-amber-500/50 bg-amber-500/10"
                      : "border-border bg-background/50"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold text-foreground">{crew.name}</h4>
                        <span className="rounded-md bg-accent px-2 py-0.5 text-xs font-medium text-muted-foreground">
                          {crew.role}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Assigned to: <strong className="text-foreground">{crew.flightNo}</strong> ·
                        Duty time left:{" "}
                        <strong
                          className={
                            crew.dutyLimitWarning
                              ? "text-amber-600 dark:text-amber-400"
                              : "text-foreground"
                          }
                        >
                          {crew.dutyRemaining}
                        </strong>
                      </p>
                    </div>

                    {crew.status !== "Off Duty" && (
                      <button
                        onClick={() => assignCrewMember(crew)}
                        className="bg-brand rounded-full px-4 py-1.5 text-xs font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.03]"
                      >
                        Assign to flight
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </Reveal>

        {/* Aircraft Turnaround & Gate Management */}
        <Reveal delay={150}>
          <GlassCard className="h-full">
            <div className="flex items-center justify-between">
              <div>
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
                  <Wrench className="h-4 w-4" /> Ground Operations
                </span>
                <h3 className="text-xl font-bold">Turnaround & Gate Control</h3>
              </div>
              <button
                onClick={handleTriggerEmergencyDispatch}
                disabled={dispatching}
                className="inline-flex items-center gap-1.5 rounded-full border border-border px-3.5 py-1.5 text-xs font-semibold transition-colors hover:bg-accent disabled:opacity-50"
              >
                {dispatching ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sliders className="h-3.5 w-3.5" />
                )}
                Deploy Hangar Relief
              </button>
            </div>

            <div className="mt-5 grid gap-4">
              {turnaroundList.map((ac) => (
                <div key={ac.id} className="rounded-2xl border border-border bg-background/50 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-display font-extrabold text-foreground">
                        {ac.tailNumber} ({ac.model})
                      </span>
                      <span className="ml-2 text-xs font-semibold text-primary">
                        {ac.flightNo} · {ac.gate}
                      </span>
                    </div>
                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                      {ac.turnaroundEstMin > 0
                        ? `${ac.turnaroundEstMin}m turnaround left`
                        : "Ready for Pushback"}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <div className="flex justify-between text-muted-foreground">
                        <span>Refueling</span>
                        <span>{ac.fuelingPct}%</span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary transition-all duration-500"
                          style={{ width: `${ac.fuelingPct}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-muted-foreground">
                        <span>Baggage Loading</span>
                        <span>{ac.baggagePct}%</span>
                      </div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-primary transition-all duration-500"
                          style={{ width: `${ac.baggagePct}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {ac.turnaroundEstMin > 0 && (
                    <button
                      onClick={() => handleFastTrackTurnaround(ac.id)}
                      className="mt-3 w-full rounded-xl border border-border py-1.5 text-xs font-semibold transition-colors hover:bg-accent"
                    >
                      Fast-Track Ground Crew Handling
                    </button>
                  )}
                </div>
              ))}
            </div>
          </GlassCard>
        </Reveal>
      </div>
    </PageShell>
  );
}
