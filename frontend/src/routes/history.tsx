import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Calendar,
  CheckCircle2,
  Clock,
  Download,
  Filter,
  History,
  Search,
  ShieldAlert,
  SlidersHorizontal,
} from "lucide-react";
import { useEffect, useState } from "react";

import { GlassCard, PageShell } from "@/components/flitz-ui";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/history")({
  head: () => ({
    meta: [
      { title: "Prediction History — Flitzz" },
      {
        name: "description",
        content: "View previous flight delay predictions and risk analysis logs.",
      },
    ],
  }),
  component: HistoryPage,
});

const ALL_HISTORY = [
  {
    id: "p1",
    flightNo: "AI-101",
    carrier: "Air India",
    origin: "DEL",
    dest: "JFK",
    status: "Delayed",
    risk: "High",
    prob: 84.2,
    delayMin: 48,
    weather: "Heavy Thunderstorm",
    timestamp: "2026-08-18 10:15",
  },
  {
    id: "p2",
    flightNo: "BA-178",
    carrier: "British Airways",
    origin: "LHR",
    dest: "BOS",
    status: "On-Time",
    risk: "Low",
    prob: 18.5,
    delayMin: 0,
    weather: "Clear Air",
    timestamp: "2026-08-18 09:40",
  },
  {
    id: "p3",
    flightNo: "AA-2342",
    carrier: "American Airlines",
    origin: "LAX",
    dest: "ORD",
    status: "Review",
    risk: "Medium",
    prob: 62.1,
    delayMin: 22,
    weather: "Airspace Congestion",
    timestamp: "2026-08-18 08:50",
  },
  {
    id: "p4",
    flightNo: "EK-203",
    carrier: "Emirates",
    origin: "DXB",
    dest: "JFK",
    status: "On-Time",
    risk: "Low",
    prob: 12.8,
    delayMin: 0,
    weather: "Clear Air",
    timestamp: "2026-08-18 07:30",
  },
  {
    id: "p5",
    flightNo: "LH-400",
    carrier: "Lufthansa",
    origin: "FRA",
    dest: "JFK",
    status: "Delayed",
    risk: "High",
    prob: 91.4,
    delayMin: 65,
    weather: "Runway Maintenance",
    timestamp: "2026-08-17 22:15",
  },
  {
    id: "p6",
    flightNo: "AF-006",
    carrier: "Air France",
    origin: "CDG",
    dest: "JFK",
    status: "Delayed",
    risk: "High",
    prob: 78.9,
    delayMin: 35,
    weather: "Crosswinds",
    timestamp: "2026-08-17 19:40",
  },
  {
    id: "p7",
    flightNo: "SQ-026",
    carrier: "Singapore Airlines",
    origin: "SIN",
    dest: "FRA",
    status: "On-Time",
    risk: "Low",
    prob: 22.4,
    delayMin: 0,
    weather: "Clear Air",
    timestamp: "2026-08-17 16:10",
  },
];

function HistoryPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState<"All" | "Low" | "Medium" | "High">("All");

  // Protection: Redirect unauthenticated users to /login
  useEffect(() => {
    if (!isAuthenticated) {
      navigate({ to: "/login" });
    }
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) return null;

  const filtered = ALL_HISTORY.filter((item) => {
    const matchesSearch =
      item.flightNo.toLowerCase().includes(search.toLowerCase()) ||
      item.origin.toLowerCase().includes(search.toLowerCase()) ||
      item.dest.toLowerCase().includes(search.toLowerCase()) ||
      item.carrier.toLowerCase().includes(search.toLowerCase());
    const matchesRisk = riskFilter === "All" || item.risk === riskFilter;
    return matchesSearch && matchesRisk;
  });

  return (
    <PageShell
      eyebrow="Protected Route • User History"
      title="Prediction History"
      description="Review previous flight delay predictions, machine learning probabilities, and risk logs."
    >
      {/* Search & Filter Controls */}
      <GlassCard className="mb-8 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="relative flex-1 min-w-[260px]">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by flight number, airline, or airport code..."
              className="w-full rounded-xl border border-input bg-background/70 py-2.5 pl-10 pr-4 text-xs outline-none transition-shadow focus:border-primary focus:shadow-glow"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
              <Filter className="h-3.5 w-3.5" /> Risk Filter:
            </span>
            {(["All", "Low", "Medium", "High"] as const).map((lvl) => (
              <button
                key={lvl}
                onClick={() => setRiskFilter(lvl)}
                className={`rounded-full px-3 py-1 text-xs font-bold transition-colors ${
                  riskFilter === lvl
                    ? "bg-primary text-primary-foreground shadow-glow"
                    : "glass hover:bg-accent"
                }`}
              >
                {lvl}
              </button>
            ))}
          </div>
        </div>
      </GlassCard>

      {/* History Table */}
      <GlassCard className="p-0 overflow-hidden border-border/60">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-border/50 bg-muted/40 uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="py-3.5 px-4">Flight & Carrier</th>
                <th className="py-3.5 px-4">Route Sector</th>
                <th className="py-3.5 px-4">Prediction Result</th>
                <th className="py-3.5 px-4">LightGBM Prob</th>
                <th className="py-3.5 px-4">Est. Delay</th>
                <th className="py-3.5 px-4">Primary Weather / Cause</th>
                <th className="py-3.5 px-4">Date & Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/40">
              {filtered.map((item) => (
                <tr key={item.id} className="hover:bg-accent/40 transition-colors">
                  <td className="py-4 px-4">
                    <p className="font-extrabold text-foreground text-sm">{item.flightNo}</p>
                    <p className="text-[11px] text-muted-foreground">{item.carrier}</p>
                  </td>
                  <td className="py-4 px-4 font-bold text-foreground">
                    {item.origin} ➔ {item.dest}
                  </td>
                  <td className="py-4 px-4">
                    <span
                      className={`rounded-full px-2.5 py-1 text-[11px] font-bold ${
                        item.risk === "High"
                          ? "bg-rose-500/10 text-rose-500 border border-rose-500/20"
                          : item.risk === "Medium"
                            ? "bg-amber-500/10 text-amber-500 border border-amber-500/20"
                            : "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                      }`}
                    >
                      {item.status} ({item.risk} Risk)
                    </span>
                  </td>
                  <td className="py-4 px-4 font-extrabold text-sm tabular-nums">{item.prob}%</td>
                  <td className="py-4 px-4 font-bold">
                    {item.delayMin > 0 ? (
                      <span className="text-rose-500">+{item.delayMin} min</span>
                    ) : (
                      <span className="text-emerald-500">0 min</span>
                    )}
                  </td>
                  <td className="py-4 px-4 text-muted-foreground font-medium">{item.weather}</td>
                  <td className="py-4 px-4 text-muted-foreground font-medium">{item.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </PageShell>
  );
}
