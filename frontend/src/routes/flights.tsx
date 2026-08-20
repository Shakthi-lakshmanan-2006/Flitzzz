import { createFileRoute } from "@tanstack/react-router";
import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { GlassCard, PageShell, Reveal, RiskBadge } from "@/components/flitz-ui";
import { riskToken, type RiskLevel } from "@/lib/flitz-data";

export const Route = createFileRoute("/flights")({
  head: () => ({
    meta: [
      { title: "Monitored Flights — FLITZZZZ" },
      {
        name: "description",
        content:
          "Browse and filter every monitored flight with live delay probability, risk band and primary risk driver.",
      },
      { property: "og:title", content: "Monitored Flights — FLITZZZZ" },
      {
        property: "og:description",
        content: "Filter monitored sectors by carrier and risk band with explainable delay scores.",
      },
    ],
  }),
  component: Flights,
});

const LEVELS: Array<RiskLevel | "All"> = ["All", "Low", "Medium", "High"];

type LiveFlight = {
  flight_id: number;
  flight_number: string;
  airline_code: string;
  airline_name: string;
  origin_airport: string;
  destination_airport: string;
  scheduled_departure?: string;
  scheduled_arrival?: string;
  distance_miles?: number;
  probability: number;
  risk_level: RiskLevel;
};

type AirlineCount = {
  airline_code: string;
  airline_name: string;
  flight_count: number;
};

type AirportCount = {
  airport_code: string;
  airport_name: string;
  airport_type: string;
  flight_count: number;
};

const API_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function Flights() {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<RiskLevel | "All">("All");
  const [airline, setAirline] = useState("All");
  const [flights, setFlights] = useState<LiveFlight[]>([]);
  const [airlineCounts, setAirlineCounts] = useState<AirlineCount[]>([]);
  const [airportCounts, setAirportCounts] = useState<AirportCount[]>([]);
  const [summary, setSummary] = useState({
    total_flights: 0,
    total_airlines: 0,
    origin_airports: 0,
    destination_airports: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    fetch(`${API_URL}/api/flights?limit=500`)
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Unable to load flights.");
        return data;
      })
      .then((data) => {
        if (!active) return;
        setFlights(data.flights ?? []);
        setSummary(data.summary ?? {
          total_flights: 0,
          total_airlines: 0,
          origin_airports: 0,
          destination_airports: 0,
        });
        setAirlineCounts(data.airline_counts ?? []);
        setAirportCounts(data.airport_counts ?? []);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Unable to load flights.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const rows = useMemo(
    () =>
      flights.filter((f) => {
        const q = query.trim().toUpperCase();
        const matchQ =
          !q ||
          f.flight_number.includes(q) ||
          f.origin_airport.includes(q) ||
          f.destination_airport.includes(q);
        return (
          matchQ &&
          (level === "All" || f.risk_level === level) &&
          (airline === "All" || f.airline_code === airline)
        );
      }).sort((a, b) => b.probability - a.probability),
    [flights, query, level, airline],
  );

  const airlines = Array.from(
    new Map(flights.map((flight) => [flight.airline_code, flight.airline_name])).entries(),
  );

  return (
    <PageShell
      eyebrow="Fleet watch"
      title="Monitored flights"
      description="Live flight records from PostgreSQL — searchable, filterable, and ranked by stored delay risk."
    >
      <Reveal>
        <GlassCard>
          <div className="mb-5 grid gap-3 sm:grid-cols-4">
            {[
              ["Total flights", summary.total_flights],
              ["Airlines", summary.total_airlines],
              ["Origin airports", summary.origin_airports],
              ["Destination airports", summary.destination_airports],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-2xl border border-border/60 bg-background/30 p-4">
                <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
                <p className="mt-2 text-2xl font-bold tabular-nums">
                  {loading ? "—" : Number(value).toLocaleString()}
                </p>
              </div>
            ))}
          </div>

          {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
          {loading && <p className="mb-4 text-sm text-muted-foreground">Loading live flights...</p>}
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search flight number or airport code"
                className="w-full rounded-full border border-input bg-background/60 py-2 pl-9 pr-4 text-sm outline-none transition-shadow focus:shadow-glow"
              />
            </div>
            <div className="flex gap-1 rounded-full border border-border p-1">
              {LEVELS.map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLevel(l)}
                  className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                    level === l ? "bg-accent text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {l}
                </button>
              ))}
            </div>
            <select
              value={airline}
              onChange={(e) => setAirline(e.target.value)}
              className="rounded-full border border-input bg-background/60 px-4 py-2 text-sm outline-none"
            >
              <option value="All">All carriers</option>
              {airlines.map(([code, name]) => (
                <option key={code} value={code}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="w-full min-w-[820px] text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wider text-muted-foreground">
                  <th className="pb-3">Flight</th>
                  <th className="pb-3">Carrier</th>
                  <th className="pb-3">Route</th>
                  <th className="pb-3">Schedule</th>
                  <th className="pb-3">Distance</th>
                  <th className="pb-3">Probability</th>
                  <th className="pb-3">Risk</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((f) => (
                  <tr
                    key={f.flight_id}
                    className="border-t border-border transition-colors hover:bg-accent/40"
                  >
                    <td className="py-3 font-semibold">{f.flight_number}</td>
                    <td className="py-3 text-muted-foreground">
                      {f.airline_name}
                    </td>
                    <td className="py-3">
                      {f.origin_airport} → {f.destination_airport}
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {f.scheduled_departure ?? "—"} – {f.scheduled_arrival ?? "—"}
                    </td>
                    <td className="py-3 tabular-nums text-muted-foreground">
                      {Number(f.distance_miles ?? 0).toLocaleString()} mi
                    </td>
                    <td className="py-3">
                      <span
                        className="font-semibold tabular-nums"
                        style={{ color: `var(--${riskToken(f.risk_level)})` }}
                      >
                        {(f.probability * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3">
                      <RiskBadge level={f.risk_level} />
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-muted-foreground">
                      No flights match those filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {!loading && !error && (
            <div className="mb-6 grid gap-5 lg:grid-cols-2">
              <div className="rounded-2xl border border-border/60 bg-background/30 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Flights by airline
                </p>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {airlineCounts.map((item) => (
                    <div key={item.airline_code} className="flex items-center justify-between rounded-xl border border-border/50 px-3 py-2">
                      <span className="truncate text-sm" title={item.airline_name}>
                        {item.airline_code} · {item.airline_name}
                      </span>
                      <strong className="ml-3 tabular-nums">{Number(item.flight_count).toLocaleString()}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-border/60 bg-background/30 p-5">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Flights by airport
                </p>
                <div className="mt-4 grid max-h-64 gap-2 overflow-y-auto sm:grid-cols-2">
                  {airportCounts.map((item) => (
                    <div key={`${item.airport_type}-${item.airport_code}`} className="flex items-center justify-between rounded-xl border border-border/50 px-3 py-2">
                      <span className="truncate text-sm" title={item.airport_name}>
                        {item.airport_code} · {item.airport_type}
                      </span>
                      <strong className="ml-3 tabular-nums">{Number(item.flight_count).toLocaleString()}</strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
                  {loading && <p className="mb-4 text-sm text-muted-foreground">Loading live flights from PostgreSQL...</p>}
                              {loading ? "Loading live flights..." : error ? "Flight data is unavailable. Check that FastAPI is running." : "No flights match those filters."}
        </GlassCard>
      </Reveal>
    </PageShell>
  );
}
