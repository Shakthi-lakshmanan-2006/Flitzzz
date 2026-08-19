import { createFileRoute } from "@tanstack/react-router";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { GlassCard, PageShell, Reveal } from "@/components/flitz-ui";
import {
  AIRPORTS,
  HOURLY_PATTERN,
  MONTHLY_TREND,
  TOP_ROUTES,
  TRAFFIC_IMPACT,
  WEATHER_IMPACT,
} from "@/lib/flitz-data";

export const Route = createFileRoute("/insights")({
  head: () => ({
    meta: [
      { title: "Network Insights — FLITZZZZ" },
      {
        name: "description",
        content:
          "Airport delay rates, departure-hour patterns, seasonal trends, route pressure, traffic intensity and weather impact.",
      },
      { property: "og:title", content: "Network Insights — FLITZZZZ" },
      {
        property: "og:description",
        content: "Interactive charts explaining where and when delays concentrate.",
      },
    ],
  }),
  component: Insights,
});

const tooltipStyle = {
  background: "var(--popover)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  color: "var(--popover-foreground)",
  fontSize: 12,
};

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <GlassCard>
      <h2 className="text-lg font-bold">{title}</h2>
      <p className="mb-4 text-sm text-muted-foreground">{subtitle}</p>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          {children as React.ReactElement}
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
}

function Insights() {
  const airports = [...AIRPORTS].sort((a, b) => b.delayRate - a.delayRate).slice(0, 10);

  return (
    <PageShell
      eyebrow="Insights"
      title="Where delays come from"
      description="Six views of the same network: airports, hours, seasons, routes, congestion and weather."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <Reveal>
          <Panel
            title="Airport delay rates"
            subtitle="Top 10 monitored hubs by historical delay share"
          >
            <BarChart data={airports}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="code" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} unit="%" />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="delayRate" radius={[6, 6, 0, 0]}>
                {airports.map((a) => (
                  <Cell
                    key={a.code}
                    fill={
                      a.delayRate > 28
                        ? "var(--risk-high)"
                        : a.delayRate > 22
                          ? "var(--risk-medium)"
                          : "var(--risk-low)"
                    }
                  />
                ))}
              </Bar>
            </BarChart>
          </Panel>
        </Reveal>

        <Reveal delay={70}>
          <Panel
            title="Departure-hour pattern"
            subtitle="Delay probability by scheduled departure hour"
          >
            <AreaChart data={HOURLY_PATTERN}>
              <defs>
                <linearGradient id="hourFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.55} />
                  <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0.04} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="hour" stroke="var(--muted-foreground)" fontSize={10} interval={2} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} unit="%" />
              <Tooltip contentStyle={tooltipStyle} />
              <Area
                dataKey="delayRate"
                stroke="var(--chart-1)"
                strokeWidth={2}
                fill="url(#hourFill)"
              />
            </AreaChart>
          </Panel>
        </Reveal>

        <Reveal delay={110}>
          <Panel
            title="Monthly & seasonal trend"
            subtitle="Delay rate against traffic volume index"
          >
            <LineChart data={MONTHLY_TREND}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="month" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line dataKey="delayRate" stroke="var(--chart-1)" strokeWidth={2.4} dot={false} />
              <Line
                dataKey="volume"
                stroke="var(--chart-2)"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            </LineChart>
          </Panel>
        </Reveal>

        <Reveal delay={150}>
          <Panel title="Route pressure" subtitle="Current predicted delay probability by sector">
            <BarChart data={TOP_ROUTES} layout="vertical">
              <CartesianGrid stroke="var(--grid-line)" horizontal={false} />
              <XAxis type="number" stroke="var(--muted-foreground)" fontSize={11} unit="%" />
              <YAxis
                type="category"
                dataKey="route"
                stroke="var(--muted-foreground)"
                fontSize={11}
                width={78}
              />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="delayRate" fill="var(--chart-2)" radius={[0, 6, 6, 0]} />
            </BarChart>
          </Panel>
        </Reveal>

        <Reveal delay={190}>
          <Panel title="Traffic intensity" subtitle="Delay rate as airport utilisation increases">
            <AreaChart data={TRAFFIC_IMPACT}>
              <defs>
                <linearGradient id="trafficFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-4)" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="var(--chart-4)" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="traffic" stroke="var(--muted-foreground)" fontSize={11} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} unit="%" />
              <Tooltip contentStyle={tooltipStyle} />
              <Area
                dataKey="delayRate"
                stroke="var(--chart-4)"
                strokeWidth={2}
                fill="url(#trafficFill)"
              />
            </AreaChart>
          </Panel>
        </Reveal>

        <Reveal delay={230}>
          <Panel title="Weather impact" subtitle="Delay rate by reported origin conditions">
            <BarChart data={WEATHER_IMPACT}>
              <CartesianGrid stroke="var(--grid-line)" vertical={false} />
              <XAxis dataKey="weather" stroke="var(--muted-foreground)" fontSize={10} />
              <YAxis stroke="var(--muted-foreground)" fontSize={11} unit="%" />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="delayRate" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </Panel>
        </Reveal>
      </div>
    </PageShell>
  );
}
