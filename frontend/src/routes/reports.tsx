import { createFileRoute, Link } from "@tanstack/react-router";
import { Download, Printer } from "lucide-react";
import { useEffect, useState } from "react";

import { FlightMap } from "@/components/flight-map";
import { GlassCard, PageShell, Reveal, RiskBadge } from "@/components/flitz-ui";
import {
  AIRLINES,
  airport,
  FLIGHTS,
  riskToken,
  WEATHER_OPTIONS,
  type PredictionResult,
} from "@/lib/flitz-data";
import { loadPrediction } from "@/lib/prediction-store";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Flight Risk Reports — FLITZZZZ" },
      {
        name: "description",
        content:
          "Generate a shareable flight-risk report with probability, drivers, route map, coordinates and model metadata.",
      },
      { property: "og:title", content: "Flight Risk Reports — FLITZZZZ" },
      {
        property: "og:description",
        content: "Print or download a polished operational delay-risk briefing.",
      },
    ],
  }),
  component: Reports,
});

function Reports() {
  const [report, setReport] = useState<PredictionResult>(FLIGHTS[0]!);

  useEffect(() => {
    const stored = loadPrediction();
    if (stored) setReport(stored);
  }, []);

  const org = airport(report.input.origin);
  const dst = airport(report.input.destination);
  const carrier =
    AIRLINES.find((a) => a.code === report.input.airline)?.name ?? report.input.airline;
  const weather =
    WEATHER_OPTIONS.find((w) => w.value === report.input.weather)?.label ?? report.input.weather;
  const token = riskToken(report.level);

  return (
    <PageShell
      eyebrow="Reports"
      title="Flight risk report"
      description="A briefing your ops team can act on — probability, drivers, geography and model provenance in one page."
    >
      <div className="mb-6 flex flex-wrap gap-3 print:hidden">
        <button
          type="button"
          onClick={() => window.print()}
          className="bg-brand inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-glow"
        >
          <Download className="h-4 w-4" /> Download PDF
        </button>
        <button
          type="button"
          onClick={() => window.print()}
          className="inline-flex items-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-semibold transition-colors hover:bg-accent"
        >
          <Printer className="h-4 w-4" /> Print
        </button>
        <Link
          to="/predict"
          className="inline-flex items-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-semibold transition-colors hover:bg-accent"
        >
          Score another flight
        </Link>
      </div>

      <Reveal>
        <GlassCard className="print:border print:shadow-none">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">
                FLITZZZZ operational briefing
              </p>
              <h2 className="font-display mt-2 text-3xl font-extrabold">
                {org.code} → {dst.code}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {carrier} · {report.input.date} · {report.input.departureTime} –{" "}
                {report.input.arrivalTime}
              </p>
            </div>
            <div className="text-right">
              <p
                className="font-display text-4xl font-extrabold tabular-nums"
                style={{ color: `var(--${token})` }}
              >
                {(report.probability * 100).toFixed(1)}%
              </p>
              <div className="mt-2 flex justify-end">
                <RiskBadge level={report.level} />
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Detail label="Origin" value={`${org.name}, ${org.city}`} />
            <Detail label="Destination" value={`${dst.name}, ${dst.city}`} />
            <Detail
              label="Sector distance"
              value={`${report.input.distanceKm.toLocaleString()} km`}
            />
            <Detail label="Weather at origin" value={weather} />
            <Detail
              label="Traffic intensity"
              value={`${(report.input.traffic * 100).toFixed(0)}%`}
            />
            <Detail label="Expected delay" value={`${report.expectedDelayMin} min`} />
            <Detail label="Model confidence" value={`${report.confidence}%`} />
            <Detail label="Generated" value={new Date(report.timestamp).toLocaleString()} />
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <div>
              <h3 className="text-lg font-bold">Contributing factors</h3>
              <div className="mt-3 grid gap-3">
                {report.factors.map((f) => (
                  <div key={f.label} className="rounded-2xl border border-border p-4">
                    <div className="flex items-center justify-between text-sm font-semibold">
                      <span>{f.label}</span>
                      <span className="tabular-nums">{f.impact}%</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{f.detail}</p>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="text-lg font-bold">Route geography</h3>
              <div className="mt-3">
                <FlightMap
                  routes={[
                    {
                      origin: report.input.origin,
                      destination: report.input.destination,
                      token,
                    },
                  ]}
                  height={280}
                />
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <Detail
                  label={`${org.code} coordinates`}
                  value={`${org.lat.toFixed(4)}, ${org.lon.toFixed(4)}`}
                />
                <Detail
                  label={`${dst.code} coordinates`}
                  value={`${dst.lat.toFixed(4)}, ${dst.lon.toFixed(4)}`}
                />
              </div>
              <div className="mt-4 rounded-2xl border border-border p-4 text-xs text-muted-foreground">
                Model: LightGBM v4.2 · AUC 0.941 · trained on 1,284,902 historical departures ·
                decision threshold 0.42 · features: schedule, congestion, weather, route history,
                carrier reliability, seasonality.
              </div>
            </div>
          </div>
        </GlassCard>
      </Reveal>
    </PageShell>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border px-4 py-3">
      <p className="text-xs uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold">{value}</p>
    </div>
  );
}
