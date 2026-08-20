import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock,
  RefreshCw,
  Send,
  Sparkles,
  User,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  GlassCard,
  PageShell,
  Reveal,
  RiskBadge,
} from "@/components/flitz-ui";
import { FlightIcon } from "@/components/flight-icon";

export const Route = createFileRoute("/rebook")({
  head: () => ({
    meta: [
      {
        title: "FLITZZ — Flight Rebooking",
      },
      {
        name: "description",
        content:
          "FLITZZ AI flight disruption recovery and passenger rebooking.",
      },
    ],
  }),
  component: RebookPage,
});

const API_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

/* ============================================================
   TYPES
   ============================================================ */

type Passenger = {
  id?: number;
  passenger_id?: number;

  name?: string;
  passenger_name?: string;

  email: string;

  pnr?: string;
  booking_reference?: string;

  seat?: string;
  seat_number?: string;

  class?: string;
  cabin_class?: string;
};

type Alternative = {
  id?: number;
  flight_id: number;

  flight_number: string;

  airline?: string;
  airline_name?: string;
  airline_code?: string;

  origin?: string;
  origin_airport?: string;

  destination?: string;
  destination_airport?: string;

  flight_date?: string;

  departure?: string;
  scheduled_departure?: string;

  arrival?: string;
  scheduled_arrival?: string;

  duration_minutes?: number;

  seats_available?: number | null;
  available_seats?: number | null;

  availability_note?: string;

  recommendation_score?: number;
  reason?: string;
};

type Flight = {
  flight_id: number;

  flight_number: string;

  airline?: string;
  airline_name?: string;

  origin?: string;
  origin_airport?: string;
  origin_name?: string;
  origin_city?: string;

  destination?: string;
  destination_airport?: string;
  destination_name?: string;
  destination_city?: string;

  scheduled_departure?: string;
  scheduled_arrival?: string;

  flight_date?: string;

  departure_delay_minutes?: number;

  route?: string;
};

type Prediction = {
  predicted_arrival_delay_minutes?: number;

  delay_probability_percent?: number;

  risk_level?: string;

  status?: string;

  recommended_action?: string;
};

type Reason = {
  title: string;
  description: string;
  severity?: string;
};

type RebookResponse = {
  success: boolean;

  flight: Flight;

  prediction?: Prediction;

  classification?: {
    delay_probability_percent?: number;
    probability_risk?: string;
    delay_probability?: number;
  };

  regression?: {
    predicted_arrival_delay_minutes?: number;
    risk_level?: string;
    recommended_action?: string;
  };

  reasons?: Reason[];

  action?: {
    level?: string;
    message?: string;
    requires_trigger?: boolean;
  };

  combined_risk?: string;

  passengers: Passenger[];

  passenger_count: number;

  total_passengers?: number;

  alternatives?: Alternative[];

  alternative_flights?: Alternative[];
};

/* ============================================================
   HELPERS
   ============================================================ */

function getPassengerName(
  passenger: Passenger,
) {
  return (
    passenger.name ||
    passenger.passenger_name ||
    "Passenger"
  );
}

function getPassengerPnr(
  passenger: Passenger,
) {
  return (
    passenger.pnr ||
    passenger.booking_reference ||
    "—"
  );
}

function getPassengerSeat(
  passenger: Passenger,
) {
  return (
    passenger.seat ||
    passenger.seat_number ||
    "—"
  );
}

function getPassengerClass(
  passenger: Passenger,
) {
  return (
    passenger.class ||
    passenger.cabin_class ||
    "—"
  );
}

function getOrigin(flight: Flight) {
  return (
    flight.origin_airport ||
    flight.origin ||
    "—"
  );
}

function getDestination(flight: Flight) {
  return (
    flight.destination_airport ||
    flight.destination ||
    "—"
  );
}

function getAlternativeOrigin(
  flight: Alternative,
) {
  return (
    flight.origin_airport ||
    flight.origin ||
    "—"
  );
}

function getAlternativeDestination(
  flight: Alternative,
) {
  return (
    flight.destination_airport ||
    flight.destination ||
    "—"
  );
}

function getAlternativeDeparture(
  flight: Alternative,
) {
  return (
    flight.scheduled_departure ||
    flight.departure ||
    "—"
  );
}

function getAlternativeArrival(
  flight: Alternative,
) {
  return (
    flight.scheduled_arrival ||
    flight.arrival ||
    "—"
  );
}

function formatTime(value?: string) {
  if (!value) return "—";

  return value.length >= 5
    ? value.slice(0, 5)
    : value;
}

function formatDate(value?: string) {
  if (!value) return "—";

  try {
    return new Date(value).toLocaleDateString(
      undefined,
      {
        day: "2-digit",
        month: "short",
        year: "numeric",
      },
    );
  } catch {
    return value;
  }
}

function delayText(value: number) {
  if (!Number.isFinite(value)) {
    return "—";
  }

  return value.toFixed(0);
}

function decisionFromDelay(delay: number) {
  if (delay >= 30) {
    return {
      label: "High risk",
      level: "High",
      description:
        "The predicted delay requires immediate operational review and passenger recovery.",
    };
  }

  if (delay >= 15) {
    return {
      label: "Medium risk",
      level: "Medium",
      description:
        "The predicted delay requires manual operational review.",
    };
  }

  return {
    label: "Low risk",
    level: "Low",
    description:
      "The predicted delay is below the disruption threshold.",
  };
}

function alternativeTimestamp(
  option: Alternative,
) {
  const date =
    option.flight_date || "";

  const departure =
    option.scheduled_departure ||
    option.departure ||
    "00:00";

  const timestamp = Date.parse(
    `${date}T${departure}`,
  );

  return Number.isFinite(timestamp)
    ? timestamp
    : Number.MAX_SAFE_INTEGER;
}

/* ============================================================
   PAGE
   ============================================================ */

export function RebookPage() {
  const [flightId, setFlightId] =
    useState("");

  const [data, setData] =
    useState<RebookResponse | null>(
      null,
    );

  const [savedPrediction, setSavedPrediction] =
    useState<Prediction | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [sending, setSending] =
    useState(false);

  const [selectedPassenger, setSelectedPassenger] =
    useState("");

  const [selectedAlternative, setSelectedAlternative] =
    useState<number | null>(null);

  const [rebooked, setRebooked] =
    useState<string | null>(null);

  const [error, setError] =
    useState<string | null>(null);

  /* ==========================================================
     LOAD FLIGHT ID FROM PREDICTION PAGE
     ========================================================== */

  useEffect(() => {
    try {
      const pending =
        localStorage.getItem(
          "flitzz:pendingAction",
        );

      if (pending) {
        const parsed =
          JSON.parse(pending);

        setSavedPrediction(
          parsed?.prediction ??
            parsed?.response?.prediction ??
            null,
        );

        const id =
          parsed?.flight?.flight_id;

        if (id) {
          setFlightId(String(id));
          return;
        }
      }

      const lastPrediction =
        localStorage.getItem(
          "flitzz:lastPrediction",
        );

      if (lastPrediction) {
        const parsed =
          JSON.parse(lastPrediction);

        setSavedPrediction(
          parsed?.response?.prediction ??
            parsed?.prediction ??
            null,
        );

        const id =
          parsed?.response?.flight
            ?.flight_id;

        if (id) {
          setFlightId(String(id));
        }
      }
    } catch {
      // Ignore invalid local storage.
    }
  }, []);

  /* ==========================================================
     LOAD REBOOKING DATA
     ========================================================== */

  async function loadRebooking(
    id = flightId,
  ) {
    const clean =
      String(id).trim();

    if (
      !clean ||
      !/^\d+$/.test(clean)
    ) {
      setError(
        "A valid database flight ID is required.",
      );
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);
    setSelectedAlternative(null);
    setRebooked(null);

    try {
      const response =
        await fetch(
          `${API_URL}/api/rebooking/${clean}`,
          {
            headers: {
              Accept:
                "application/json",
            },
          },
        );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Rebooking API returned ${response.status}.`,
        );
      }

      setData(
        body as RebookResponse,
      );

      if (
        body?.passengers?.length
      ) {
        setSelectedPassenger(
          body.passengers[0].email,
        );
      }
    } catch (err) {
      console.error(
        "FLITZZ rebooking error:",
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : "Unable to load rebooking data.",
      );
    } finally {
      setLoading(false);
    }
  }

  /* ==========================================================
     SEND PASSENGER NOTIFICATIONS
     ========================================================== */

  async function sendNotifications() {
    if (!data) return;

    if (
      data.passenger_count === 0
    ) {
      toast.error(
        "No passengers are available for notification.",
      );
      return;
    }

    setSending(true);

    try {
      const reason =
        data.reasons?.[0]
          ?.description ||
        "Operational delay detected by the FLITZZ prediction system.";

      const response =
        await fetch(
          `${API_URL}/api/notifications/${data.flight.flight_id}/send`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
              Accept:
                "application/json",
            },
            body: JSON.stringify({
              reason,
            }),
          },
        );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            `Notification API returned ${response.status}.`,
        );
      }

      const count =
        body?.recipient_count ??
        body?.sent_count ??
        data.passenger_count;

      toast.success(
        `Notification sent to ${count} passenger(s).`,
      );

      if (body?.failed_count) {
        toast.error(
          `${body.failed_count} notification(s) failed.`,
        );
      }
    } catch (err) {
      console.error(
        "Notification error:",
        err,
      );

      toast.error(
        err instanceof Error
          ? err.message
          : "Unable to notify passengers.",
      );
    } finally {
      setSending(false);
    }
  }

  /* ==========================================================
     REBOOK PASSENGER
     ========================================================== */

  async function confirmRebook(
    option: Alternative,
  ) {
    if (
      !data ||
      !selectedPassenger
    ) {
      toast.error(
        "Select a passenger first.",
      );
      return;
    }

    setSelectedAlternative(
      option.flight_id,
    );

    try {
      const response =
        await fetch(
          `${API_URL}/api/rebooking/confirm`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
              Accept:
                "application/json",
            },
            body: JSON.stringify({
              flight_id:
                data.flight.flight_id,

              passenger_email:
                selectedPassenger,

              alternative_flight_id:
                option.flight_id,
            }),
          },
        );

      const body =
        await response.json();

      if (!response.ok) {
        throw new Error(
          body?.detail ||
            "Rebooking failed.",
        );
      }

      setRebooked(
        `${selectedPassenger}:${option.flight_id}`,
      );

      toast.success(
        `Rebooking confirmed for ${
          body?.passenger?.name ||
          body?.passenger?.passenger_name ||
          "passenger"
        }.`,
      );
    } catch (err) {
      console.error(
        "Rebooking error:",
        err,
      );

      setSelectedAlternative(null);

      toast.error(
        err instanceof Error
          ? err.message
          : "Unable to confirm rebooking.",
      );
    }
  }

  /* ==========================================================
     DERIVED DATA
     ========================================================== */

  const delay =
    Number(
      savedPrediction
        ?.predicted_arrival_delay_minutes ??
        data?.prediction
        ?.predicted_arrival_delay_minutes ??
        data?.regression
          ?.predicted_arrival_delay_minutes ??
        0,
    );

  const probability =
    Number(
      savedPrediction
        ?.delay_probability_percent ??
        data?.prediction
        ?.delay_probability_percent ??
        data?.classification
          ?.delay_probability_percent ??
        0,
    );

  const decision =
    decisionFromDelay(delay);

  const activePassenger =
    useMemo(
      () =>
        data?.passengers?.find(
          (p) =>
            p.email ===
            selectedPassenger,
        ) ||
        data?.passengers?.[0],
      [
        data,
        selectedPassenger,
      ],
    );

  const alternatives =
    useMemo(() => {
      const source =
        data?.alternatives ||
        data?.alternative_flights ||
        [];

      const unique =
        new Map<
          number,
          Alternative
        >();

      source.forEach(
        (option) => {
          if (
            option.flight_id !==
            data?.flight?.flight_id
          ) {
            unique.set(
              option.flight_id,
              option,
            );
          }
        },
      );

      return Array.from(
        unique.values(),
      ).sort(
        (a, b) =>
          alternativeTimestamp(a) -
          alternativeTimestamp(b),
      );
    }, [data]);

  /* ============================================================
     UI
     ============================================================ */

  return (
    <PageShell
      eyebrow="Smart Disruption Recovery"
      title="AI Flight Rebooking"
      description="Review the delayed flight, affected passengers, recommended recovery options and passenger notifications."
    >
      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="mb-6 rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <p className="font-semibold">
            Rebooking service error
          </p>

          <p className="mt-1">
            {error}
          </p>

          <p className="mt-1 text-xs opacity-80">
            Check PostgreSQL and FastAPI at{" "}
            {API_URL}.
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">

        {/* ====================================================
            LEFT
        ==================================================== */}

        <div className="grid gap-6">

          {/* FLIGHT LOOKUP */}

          <Reveal>
            <GlassCard>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                <AlertTriangle className="h-4 w-4" />
                Flight recovery
              </div>

              <h2 className="mt-2 text-xl font-bold">
                Load flight
              </h2>

              <p className="mt-2 text-xs leading-5 text-muted-foreground">
                Enter the database flight ID or open
                this page directly from the prediction
                result.
              </p>

              <div className="mt-5 flex gap-2">
                <input
                  value={flightId}
                  onChange={(event) =>
                    setFlightId(
                      event.target.value.replace(
                        /\D/g,
                        "",
                      ),
                    )
                  }
                  placeholder="Flight ID"
                  className="w-full rounded-xl border border-input bg-background/60 px-3 py-2.5 text-sm outline-none focus:shadow-glow"
                />

                <button
                  onClick={() =>
                    loadRebooking()
                  }
                  disabled={loading}
                  className="bg-brand inline-flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-glow disabled:opacity-60"
                >
                  {loading ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}

                  Load
                </button>
              </div>
            </GlassCard>
          </Reveal>

          {/* PASSENGER COUNT */}

          {data && (
            <Reveal delay={60}>
              <GlassCard>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                  <Users className="h-4 w-4" />
                  Passenger impact
                </div>

                <div className="mt-4 rounded-2xl border border-primary/20 bg-primary/5 p-6 text-center">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                    Total passengers
                  </p>
                  <p className="mt-2 text-5xl font-black text-primary">
                    {data.total_passengers ?? data.passenger_count}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Passenger records are protected and handled by the notification workflow.
                  </p>
                </div>
              </GlassCard>
            </Reveal>
          )}

        </div>

        <div className="grid gap-6">

          {data && (
            <>
          {/* =================================================
                  FLIGHT HEADER
                ================================================= */}

              <Reveal delay={80}>
                <GlassCard className="relative overflow-hidden border-primary/30">

                  <div className="flex flex-wrap items-start justify-between gap-5">

                    <div>

                      <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/10 px-3 py-1.5 text-xs font-semibold text-destructive">
                        <Clock className="h-3.5 w-3.5" />

                        Predicted delay +
                        {delayText(delay)}
                        {" "}
                        min
                      </span>

                      <h2 className="mt-3 text-2xl font-extrabold">
                        Flight{" "}
                        {data.flight.flight_number}
                      </h2>

                      <p className="mt-1 text-base font-semibold">
                        {getOrigin(
                          data.flight,
                        )}
                        {" → "}
                        {getDestination(
                          data.flight,
                        )}
                      </>
                    )}

                      <p className="mt-1 text-xs text-muted-foreground">
                        Flight ID{" "}
                        {data.flight.flight_id}
                        {" · "}
                        {data.flight.airline_name ||
                          data.flight.airline ||
                          "Airline"}
                      </p>

                      <p className="mt-1 text-xs text-muted-foreground">
                        Scheduled departure{" "}
                        <strong className="text-foreground">
                          {formatTime(
                            data.flight
                              .scheduled_departure,
                          )}
                        </strong>

                        {" · "}

                        {formatDate(
                          data.flight.flight_date,
                        )}
                      </p>

                    </div>

                    <RiskBadge
                      level={
                        decision.level as any
                      }
                    />

                  </div>

                  {/* METRICS */}

                  <div className="mt-6 grid gap-3 sm:grid-cols-3">

                    <div className="rounded-2xl border border-border bg-background/40 p-4">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Delay
                      </p>

                      <p className="mt-1 text-2xl font-black">
                        {delayText(delay)}
                        <span className="ml-1 text-sm font-medium">
                          min
                        </span>
                      </p>
                    </div>

                    <div className="rounded-2xl border border-border bg-background/40 p-4">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Risk probability
                      </p>

                      <p className="mt-1 text-2xl font-black">
                        {Number.isFinite(
                          probability,
                        )
                          ? probability.toFixed(1)
                          : "—"}
                        %
                      </p>
                    </div>

                    <div className="rounded-2xl border border-border bg-background/40 p-4">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Passengers
                      </p>

                      <p className="mt-1 text-2xl font-black">
                        {data.passenger_count}
                      </p>
                    </div>

                  </div>

                  {/* NOTIFICATION */}

                  <div className="mt-5 rounded-2xl border border-primary/20 bg-primary/5 p-4">

                    <div className="flex flex-wrap items-center justify-between gap-4">

                      <div className="flex items-start gap-3">

                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                          <Bell className="h-5 w-5" />
                        </div>

                        <div>

                          <p className="text-[10px] font-bold uppercase tracking-wider text-primary">
                            Passenger notification
                          </p>

                          <p className="mt-1 text-lg font-black">
                            {decision.label}
                          </p>

                          <p className="mt-1 max-w-xl text-xs leading-5 text-muted-foreground">
                            {decision.description}
                          </p>

                        </div>

                      </div>

                      <button
                        onClick={
                          sendNotifications
                        }
                        disabled={
                          sending ||
                          data.passenger_count ===
                            0
                        }
                        className="bg-brand inline-flex items-center gap-2 rounded-full px-5 py-3 text-xs font-bold text-primary-foreground shadow-glow transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {sending ? (
                          <>
                            <RefreshCw className="h-4 w-4 animate-spin" />
                            Sending…
                          </>
                        ) : (
                          <>
                            <Send className="h-4 w-4" />
                            Send notification
                          </>
                        )}
                      </button>

                    </div>

                  </div>

                </GlassCard>
              </Reveal>

              {/* =================================================
                  RECOMMENDATION
              ================================================= */}

              <Reveal delay={120}>
                <GlassCard>

                  <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                    <Sparkles className="h-4 w-4" />
                    AI recommendation
                  </div>

                  <h2 className="mt-2 text-xl font-bold">
                    Recovery recommendation
                  </h2>

                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {data.action?.message ||
                      data.regression
                        ?.recommended_action ||
                      "Review the upcoming same-route flights below and select the most suitable option."}
                  </p>

                  {data.reasons &&
                    data.reasons.length >
                      0 && (
                      <div className="mt-4 grid gap-2">
                        {data.reasons.map(
                          (
                            reason,
                            index,
                          ) => (
                            <div
                              key={`${reason.title}-${index}`}
                              className="rounded-xl border border-border bg-background/40 p-3"
                            >
                              <p className="text-sm font-semibold">
                                {reason.title}
                              </p>

                              <p className="mt-1 text-xs leading-5 text-muted-foreground">
                                {
                                  reason.description
                                }
                              </p>
                            </div>
                          ),
                        )}
                      </div>
                    )}

                </GlassCard>
              </Reveal>

              {/* =================================================
                  ALTERNATIVES
              ================================================= */}

              <Reveal delay={160}>
                <GlassCard>

                  <div className="flex flex-wrap items-end justify-between gap-3">

                    <div>
                      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                        <Clock className="h-4 w-4" />
                        Same-route recovery
                      </div>

                      <h2 className="mt-2 text-xl font-bold">
                        Recommended alternative flights
                      </h2>

                      <p className="mt-1 text-xs text-muted-foreground">
                        Upcoming flights from{" "}
                        {getOrigin(
                          data.flight,
                        )}
                        {" → "}
                        {getDestination(
                          data.flight,
                        )}
                      </p>
                    </div>

                    <div className="rounded-xl border border-primary/20 bg-primary/5 px-4 py-2">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                        Options
                      </p>

                      <p className="text-xl font-black text-primary">
                        {alternatives.length}
                      </p>
                    </div>

                  </div>

                  <div className="mt-5 grid gap-3">

                    {alternatives.length ===
                    0 ? (
                      <div className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-5 text-sm text-muted-foreground">
                        No upcoming same-route
                        alternative flights were found
                        in the database.
                      </div>
                    ) : (
                      alternatives.map(
                        (
                          option,
                          index,
                        ) => {
                          const selected =
                            selectedAlternative ===
                            option.flight_id;

                          const completed =
                            rebooked ===
                            `${selectedPassenger}:${option.flight_id}`;

                          return (
                            <div
                              key={
                                option.flight_id
                              }
                              className={`rounded-2xl border p-4 transition-all ${
                                selected
                                  ? "border-primary bg-primary/5"
                                  : "border-border bg-background/20 hover:bg-accent/20"
                              }`}
                            >

                              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">

                                <div className="flex min-w-0 items-start gap-3">

                                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                                    <FlightIcon className="h-5 w-5" />
                                  </div>

                                  <div className="min-w-0">

                                    <div className="flex flex-wrap items-center gap-2">

                                      <p className="text-lg font-extrabold">
                                        {
                                          option.flight_number
                                        }
                                      </p>

                                      {index ===
                                        0 && (
                                        <span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] font-bold text-primary">
                                          BEST OPTION
                                        </span>
                                      )}

                                    </div>

                                    <p className="mt-1 text-xs text-muted-foreground">
                                      {option.airline_name ||
                                        option.airline ||
                                        option.airline_code ||
                                        "Airline"}
                                    </p>

                                    <p className="mt-2 text-sm font-semibold">
                                      {getAlternativeOrigin(
                                        option,
                                      )}
                                      {" → "}
                                      {getAlternativeDestination(
                                        option,
                                      )}
                                    </p>

                                    <p className="mt-1 text-xs text-muted-foreground">
                                      {formatDate(
                                        option.flight_date,
                                      )}
                                      {" · "}
                                      Departure{" "}
                                      {formatTime(
                                        getAlternativeDeparture(
                                          option,
                                        ),
                                      )}
                                      {" · "}
                                      Arrival{" "}
                                      {formatTime(
                                        getAlternativeArrival(
                                          option,
                                        ),
                                      )}
                                    </p>

                                  </div>

                                </div>

                                <div className="flex flex-wrap items-center gap-3">

                                  {option.recommendation_score !==
                                    undefined && (
                                    <div className="rounded-xl border border-primary/20 bg-primary/5 px-3 py-2 text-center">
                                      <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">
                                        Score
                                      </p>

                                      <p className="text-lg font-black text-primary">
                                        {Number(
                                          option.recommendation_score,
                                        ).toFixed(
                                          0,
                                        )}
                                      </p>
                                    </div>
                                  )}

                                  <button
                                    onClick={() =>
                                      confirmRebook(
                                        option,
                                      )
                                    }
                                    disabled={
                                      !activePassenger ||
                                      selected ||
                                      completed
                                    }
                                    className="inline-flex items-center gap-2 rounded-xl border border-primary/30 bg-primary/10 px-4 py-2.5 text-xs font-bold text-primary transition hover:bg-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
                                  >
                                    {completed ? (
                                      <>
                                        <CheckCircle2 className="h-4 w-4" />
                                        Rebooked
                                      </>
                                    ) : selected ? (
                                      <>
                                        <RefreshCw className="h-4 w-4 animate-spin" />
                                        Processing…
                                      </>
                                    ) : (
                                      <>
                                        <CheckCircle2 className="h-4 w-4" />
                                        Rebook passenger
                                      </>
                                    )}
                                  </button>

                                </div>

                              </div>

                              {option.reason && (
                                <div className="mt-3 rounded-xl border border-border/60 bg-background/30 px-3 py-2">
                                  <p className="text-xs text-muted-foreground">
                                    <strong className="text-foreground">
                                      Recommendation:
                                    </strong>{" "}
                                    {
                                      option.reason
                                    }
                                  </p>
                                </div>
                              )}

                            </div>
                          );
                        },
                      )
                    )}

                  </div>

                </GlassCard>
              </Reveal>

            </>
          )}

        </div>
      </div>
    </PageShell>
  );
}