import { createFileRoute } from "@tanstack/react-router";
import { Search } from "lucide-react";
import { useMemo, useState } from "react";

import { GlassCard, PageShell, Reveal, RiskBadge } from "@/components/flitz-ui";
import { AIRLINES, FLIGHTS, riskToken, type RiskLevel } from "@/lib/flitz-data";

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

function Flights() {
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<RiskLevel | "All">("All");
  const [airline, setAirline] = useState("All");

  const rows = useMemo(
    () =>
      FLIGHTS.filter((f) => {
        const q = query.trim().toUpperCase();
        const matchQ =
          !q ||
          f.flightNo.includes(q) ||
          f.input.origin.includes(q) ||
          f.input.destination.includes(q);
        return (
          matchQ &&
          (level === "All" || f.level === level) &&
          (airline === "All" || f.input.airline === airline)
        );
      }).sort((a, b) => b.probability - a.probability),
    [query, level, airline],
  );

  return (
    <PageShell
      eyebrow="Fleet watch"
      title="Monitored flights"
      description="Every scored sector in one place — searchable, filterable, and ranked by delay probability."
    >
      <Reveal>
        <GlassCard>
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
              {AIRLINES.map((a) => (
                <option key={a.code} value={a.code}>
                  {a.name}
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
                    key={f.id}
                    className="border-t border-border transition-colors hover:bg-accent/40"
                  >
                    <td className="py-3 font-semibold">{f.flightNo}</td>
                    <td className="py-3 text-muted-foreground">
                      {AIRLINES.find((a) => a.code === f.input.airline)?.name}
                    </td>
                    <td className="py-3">
                      {f.input.origin} → {f.input.destination}
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {f.input.departureTime} – {f.input.arrivalTime}
                    </td>
                    <td className="py-3 tabular-nums text-muted-foreground">
                      {f.input.distanceKm.toLocaleString()} km
                    </td>
                    <td className="py-3">
                      <span
                        className="font-semibold tabular-nums"
                        style={{ color: `var(--${riskToken(f.level)})` }}
                      >
                        {(f.probability * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3">
                      <RiskBadge level={f.level} />
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
        </GlassCard>
      </Reveal>
    </PageShell>
  );
}
