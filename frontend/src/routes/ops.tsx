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
  selected?: boolean;
  assignmentId?: number;
};

type PredictionContext = {
  flight?: { flight_id?: number; flight_number?: string };
  prediction?: {
    predicted_arrival_delay_minutes?: number;
    risk_level?: string;
    recommended_action?: string;
  };
  response?: {
    flight?: { flight_id?: number; flight_number?: string };
    prediction?: PredictionContext["prediction"];
    action?: { level?: string; message?: string };
    reasons?: Array<{ title: string; description: string }>;
  };
};

type Assignment = {
  assignment_id: number;
  crew_id: number;
  crew_name: string;
  assignment_role: string;
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

const INITIAL_CREW: CrewMember[] = [];

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
  const [prediction, setPrediction] = useState<PredictionContext | null>(null);
  const [loadingCrew, setLoadingCrew] = useState(false);
  const [savingAssignments, setSavingAssignments] = useState(false);

  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

  function recommendationForDelay(delay: number) {
    if (delay >= 30) {
      return {
        label: "Automatic recovery staffing",
        roles: ["Captain", "First Officer", "Lead Attendant"] as CrewMember["role"][],
        detail: "The prediction is high risk. Select a relief flight deck pair and lead cabin crew.",
      };
    }
    if (delay >= 15) {
      return {
        label: "Manual crew review",
        roles: ["First Officer", "Lead Attendant"] as CrewMember["role"][],
        detail: "The prediction requires review. Select available relief crew before dispatch.",
      };
    }
    return {
      label: "Monitor current crew",
      roles: [] as CrewMember["role"][],
      detail: "The predicted delay is below the crew intervention threshold.",
    };
  }

  const predictedDelay = Number(
    prediction?.response?.prediction?.predicted_arrival_delay_minutes ??
      prediction?.prediction?.predicted_arrival_delay_minutes ??
      0,
  );
  const staffingRecommendation = recommendationForDelay(predictedDelay);

  useEffect(() => {
    try {
      const stored = localStorage.getItem("flitzz:lastPrediction");
      if (stored) {
        const parsed = JSON.parse(stored) as PredictionContext;
        setPrediction(parsed);
        const flight = parsed.response?.flight ?? parsed.flight;
        if (flight?.flight_id) setCrewFlightId(String(flight.flight_id));
      }
    } catch {
      toast.error("Unable to read the latest prediction.");
    }
  }, []);

  useEffect(() => {
    async function loadCrew() {
      setLoadingCrew(true);
      try {
        const flightId = Number(crewFlightId);
        const [crewResponse, assignmentResponse] = await Promise.all([
          fetch(`${apiUrl}/api/crew`),
          Number.isInteger(flightId) && flightId > 0
            ? fetch(`${apiUrl}/api/crew-assignments/${flightId}`)
            : Promise.resolve(null),
        ]);

        if (!crewResponse.ok) {
          const detail = await crewResponse.text();
          throw new Error(
            detail || `Crew API returned HTTP ${crewResponse.status}.`,
          );
        }

        const members = await crewResponse.json();
        const assignments =
          assignmentResponse?.ok
            ? ((await assignmentResponse.json()) as Assignment[])
            : [];
        const assignedByCrew = new Map(assignments.map((assignment) => [assignment.crew_id, assignment]));
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
            flightNo: assignedByCrew.has(Number(member.crew_id)) ? `Flight ${flightId}` : "Available",
            dutyRemaining: "Available",
            status: assignedByCrew.has(Number(member.crew_id)) ? "Assigned" : member.status === "ACTIVE" ? "Standby" : "Off Duty",
            selected: assignedByCrew.has(Number(member.crew_id)),
            assignmentId: assignedByCrew.get(Number(member.crew_id))?.assignment_id,
          })),
        );
      } catch {
        toast.error("Unable to load crew members from PostgreSQL.");
      } finally {
        setLoadingCrew(false);
      }
    }
    void loadCrew();
  }, [apiUrl, crewFlightId]);

  function toggleCrewSelection(crewId: string) {
    setCrewList((current) => current.map((member) =>
      member.id === crewId ? { ...member, selected: !member.selected } : member,
    ));
  }

  async function saveCrewAssignments() {
    const flightId = Number(crewFlightId);
    const selected = crewList.filter((crew) => crew.selected && crew.crewId);
    if (!Number.isInteger(flightId) || flightId <= 0) {
      toast.error("Enter a valid flight ID before assigning crew.");
      return;
    }
    if (selected.length === 0) {
      toast.error("Select at least one crew member.");
      return;
    }

    setSavingAssignments(true);
    try {
      const response = await fetch(`${apiUrl}/api/crew-assignments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          flight_id: flightId,
          notes: prediction?.response?.action?.message ?? "Prediction-driven crew assignment",
          assignments: selected.map((crew) => ({ crew_id: crew.crewId, assignment_role: crew.role })),
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Crew assignment failed.");
      setCrewList((current) => current.map((member) =>
        member.selected ? { ...member, flightNo: `Flight ${flightId}`, status: "Assigned" } : member,
      ));
      toast.success(`${selected.length} crew assignment(s) saved to PostgreSQL.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Crew assignment failed.");
    } finally {
      setSavingAssignments(false);
    }
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
                  {crewList.filter((crew) => crew.status === "Standby").length} Available
                </span>
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-primary/20 bg-primary/5 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-primary">
                    Prediction-driven staffing
                  </p>
                  <p className="mt-1 text-lg font-black">
                    {prediction ? `${predictedDelay.toFixed(0)} min predicted delay` : "No prediction loaded"}
                  </p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">
                    {staffingRecommendation.detail}
                  </p>
                </div>
                <span className="rounded-full bg-background/70 px-3 py-1.5 text-xs font-semibold text-primary">
                  {staffingRecommendation.label}
                </span>
              </div>
              {staffingRecommendation.roles.length > 0 && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Suggested roles: {staffingRecommendation.roles.join(" · ")}
                </p>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between gap-3">
              <p className="text-xs text-muted-foreground">
                {loadingCrew ? "Loading crew from PostgreSQL..." : "Select crew members to assign to this flight."}
              </p>
              <button
                onClick={saveCrewAssignments}
                disabled={savingAssignments || loadingCrew}
                className="bg-brand inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-semibold text-primary-foreground shadow-glow disabled:opacity-50"
              >
                {savingAssignments && <RefreshCw className="h-3.5 w-3.5 animate-spin" />}
                Save assignments
              </button>
            </div>

            <div className="mt-5 grid gap-3">
              {crewList.length === 0 && !loadingCrew ? (
                <div className="rounded-2xl border border-dashed border-border p-5 text-sm text-muted-foreground">
                  No active crew members were returned by the database.
                </div>
              ) : crewList.map((crew) => (
                <div
                  key={crew.id}
                  className={`rounded-2xl border p-4 transition-all ${
                    crew.selected
                      ? "border-primary bg-primary/5"
                      : crew.dutyLimitWarning
                      ? "border-amber-500/50 bg-amber-500/10"
                      : "border-border bg-background/50"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <label className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={crew.selected ?? false}
                        onChange={() => toggleCrewSelection(crew.id)}
                        disabled={crew.status === "Off Duty"}
                        className="mt-1 h-4 w-4 accent-primary"
                      />
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
                    </label>
                    {staffingRecommendation.roles.includes(crew.role) && crew.status !== "Off Duty" && (
                      <span className="rounded-full border border-primary/20 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-primary">
                        Suggested
                      </span>
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
