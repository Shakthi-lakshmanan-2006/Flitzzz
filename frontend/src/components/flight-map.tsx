import { FLIGHT_MAP_ICON_PATH } from "@/components/flight-icon";
import { airport, type Airport } from "@/lib/flitz-data";

const W = 1000;
const H = 500;

function project(a: Airport) {
  return { x: ((a.lon + 180) / 360) * W, y: ((90 - a.lat) / 180) * H };
}

export type MapRoute = {
  origin: string;
  destination: string;
  riskScore?: number | undefined; // 0 - 100
  token?: "risk-low" | "risk-medium" | "risk-high" | string | undefined;
};

export function getRouteRiskToken(r: MapRoute): "risk-low" | "risk-medium" | "risk-high" {
  if (r.token) {
    const t = r.token.toLowerCase();
    if (t.includes("low")) return "risk-low";
    if (t.includes("med") || t.includes("medium")) return "risk-medium";
    if (t.includes("high")) return "risk-high";
  }
  if (r.riskScore !== undefined) {
    if (r.riskScore < 50) return "risk-low";
    if (r.riskScore <= 75) return "risk-medium";
    return "risk-high";
  }
  return "risk-low";
}

// World Continent Landmass Outlines for realistic global radar map view
const CONTINENTS = [
  // North America
  "M 110,80 Q 210,50 310,95 Q 320,170 270,240 Q 180,250 120,180 Z",
  // South America
  "M 260,260 Q 340,280 320,380 Q 280,480 250,420 Q 230,320 260,260 Z",
  // Europe
  "M 460,75 Q 560,65 580,135 Q 520,175 470,145 Z",
  // Africa
  "M 450,170 Q 580,170 590,280 Q 530,410 470,360 Q 430,260 450,170 Z",
  // Asia & Middle East
  "M 570,65 Q 860,45 910,165 Q 830,280 650,220 Q 560,150 570,65 Z",
  // Australia & Oceania
  "M 800,320 Q 910,310 920,400 Q 840,440 790,380 Z",
];

export function FlightMap({
  routes,
  showLabels = true,
  showLegend = true,
  height = 460,
  animate = true,
}: {
  routes: MapRoute[];
  showLabels?: boolean;
  showLegend?: boolean;
  height?: number;
  animate?: boolean;
}) {
  const nodes = new Map<
    string,
    { airport: Airport; highestRisk: "risk-low" | "risk-medium" | "risk-high" }
  >();

  for (const r of routes) {
    const token = getRouteRiskToken(r);
    const org = airport(r.origin);
    const dst = airport(r.destination);

    const updateNode = (code: string, ap: Airport) => {
      const existing = nodes.get(code);
      if (!existing) {
        nodes.set(code, { airport: ap, highestRisk: token });
      } else {
        const priority = { "risk-low": 1, "risk-medium": 2, "risk-high": 3 };
        if (priority[token] > priority[existing.highestRisk]) {
          nodes.set(code, { airport: ap, highestRisk: token });
        }
      }
    };

    updateNode(r.origin, org);
    updateNode(r.destination, dst);
  }

  return (
    <div
      className="grid-lines relative w-full overflow-hidden rounded-3xl border border-border bg-card/75 shadow-elevated"
      style={{ height }}
    >
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-full w-full"
        role="img"
        aria-label="Real-time Global Air Network Radar Map"
      >
        <defs>
          <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* High-Definition Global Network Map Background */}
        <image
          href="/world-map-bg.png"
          x="0"
          y="0"
          width={W}
          height={H}
          preserveAspectRatio="none"
          opacity={0.96}
        />

        {/* Global Continent Vector Accents */}
        <g opacity={0.15}>
          {CONTINENTS.map((pathD, idx) => (
            <path key={idx} d={pathD} fill="var(--primary)" stroke="none" />
          ))}
        </g>

        {/* Latitude & Longitude Grid Lines */}
        {[-60, -30, 0, 30, 60].map((lat) => {
          const y = ((90 - lat) / 180) * H;
          return (
            <line
              key={lat}
              x1={0}
              x2={W}
              y1={y}
              y2={y}
              stroke="var(--grid-line)"
              strokeDasharray="4 10"
            />
          );
        })}

        {/* Flight Routes - 3-Color Protocol */}
        {routes.map((r, i) => {
          const a = project(airport(r.origin));
          const b = project(airport(r.destination));
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2 - Math.abs(b.x - a.x) * 0.22 - 24;
          const d = `M ${a.x} ${a.y} Q ${mx} ${my} ${b.x} ${b.y}`;
          const token = getRouteRiskToken(r);
          const stroke = `var(--${token})`;

          return (
            <g key={`${r.origin}-${r.destination}-${i}`}>
              <path
                d={d}
                fill="none"
                stroke={stroke}
                strokeWidth={token === "risk-high" ? 2.4 : 1.8}
                opacity={token === "risk-high" ? 0.95 : 0.82}
                filter="url(#softGlow)"
              />
              {animate && (
                <g>
                  <path
                    id={`p-${i}`}
                    d={d}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={2.4}
                    strokeDasharray="28 970"
                    className="animate-dash"
                    style={{ animationDelay: `${i * 0.65}s` }}
                    opacity={0.9}
                  />
                  <g>
                    <path d={FLIGHT_MAP_ICON_PATH} fill={stroke}>
                      <animateMotion
                        dur={`${8 + (i % 4) * 1.5}s`}
                        repeatCount="indefinite"
                        rotate="auto"
                        begin={`${i * 0.75}s`}
                        path={d}
                      />
                    </path>
                  </g>
                </g>
              )}
            </g>
          );
        })}

        {/* Airport Nodes with Radar Pulses */}
        {[...nodes.values()].map(({ airport: a, highestRisk }) => {
          const p = project(a);
          const strokeColor = `var(--${highestRisk})`;
          return (
            <g key={a.code}>
              <circle cx={p.x} cy={p.y} r={12} fill={strokeColor} opacity={0.18}>
                <animate attributeName="r" values="4;14;4" dur="3s" repeatCount="indefinite" />
                <animate
                  attributeName="opacity"
                  values="0.3;0.05;0.3"
                  dur="3s"
                  repeatCount="indefinite"
                />
              </circle>
              <circle
                cx={p.x}
                cy={p.y}
                r={4.2}
                fill={strokeColor}
                stroke="#ffffff"
                strokeWidth={1}
              />
              {showLabels && (
                <text
                  x={p.x + 9}
                  y={p.y - 8}
                  fontSize={11}
                  fontWeight={700}
                  fill="var(--foreground)"
                  opacity={0.9}
                >
                  {a.code}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* 3-Color Status Legend Overlay */}
      {showLegend && (
        <div className="glass absolute bottom-4 left-4 flex flex-wrap items-center gap-4 rounded-2xl px-4 py-2.5 text-xs font-semibold shadow-md">
          <div className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full shadow-sm"
              style={{ background: "var(--risk-low)" }}
            />
            <span>🟢 Green: Low Delay Risk (&lt;50%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full shadow-sm"
              style={{ background: "var(--risk-medium)" }}
            />
            <span>🟡 Yellow: Medium Risk (50–75%, Manual Review)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full shadow-sm"
              style={{ background: "var(--risk-high)" }}
            />
            <span>🔴 Red: High Risk (&gt;75%, Auto-Intervention)</span>
          </div>
        </div>
      )}
    </div>
  );
}
