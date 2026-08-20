import {
  createFileRoute,
  Link,
  useNavigate,
} from "@tanstack/react-router";

import {
  Loader2,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  ArrowRight,
  Database,
  Search,
  Activity,
  TrendingUp,
  ShieldCheck,
} from "lucide-react";

import {
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { FlightMap } from "@/components/flight-map";
import {
  GlassCard,
  PageShell,
  Reveal,
} from "@/components/flitz-ui";

import { savePrediction } from "@/lib/prediction-store";
import { useAuth } from "@/lib/auth";


/* ============================================================
   ROUTE
   ============================================================ */

export const Route = createFileRoute("/predict")({
  head: () => ({
    meta: [
      {
        title: "Predict Flight Delay — FLITZZZZ",
      },
      {
        name: "description",
        content:
          "Look up a flight from PostgreSQL and run the FLITZZ ML prediction.",
      },
    ],
  }),
  component: Predict,
});


/* ============================================================
   API
   ============================================================ */

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";


/* ============================================================
   TYPES
   ============================================================ */

type OperationalReason = {
  type?: string;
  title: string;
  description: string;
  severity: "HIGH" | "MODERATE" | "LOW" | string;
  value?: number;
};

type BackendPredictionResponse = {
  success: boolean;

  lookup: {
    input: string;
    resolved_by: string;
    resolved_value: string;
  };

  flight: {
    flight_id: number;
    source_row_id?: number;
    flight_number: string;
    tail_number?: string;
    flight_date: string;

    airline: string;
    airline_name?: string;

    origin_airport: string;
    origin_name?: string;
    origin_city?: string;

    destination_airport: string;
    destination_name?: string;
    destination_city?: string;

    scheduled_departure?: string;
    scheduled_arrival?: string;
    departure_time?: string;
    arrival_time?: string;

    scheduled_time_minutes?: number;
    elapsed_time_minutes?: number;
    air_time_minutes?: number;
    taxi_out_minutes?: number;
    taxi_in_minutes?: number;
    departure_delay_minutes?: number;

    wheels_off?: string;
    wheels_on?: string;

    distance_miles?: number;

    diverted?: boolean;
    cancelled?: boolean;

    route: string;
  };

  model_features: Record<string, string | number | boolean | null>;

  derived_features?: Record<
    string,
    string | number | boolean | null
  >;

  classification: {
    delay_probability: number;
    delay_probability_percent: number;
    delayed_15: boolean;
    classification_threshold?: number;
    status: string;
    probability_risk: string;
    feature_count?: number;
    features?: string[];
    categorical_features?: string[];
    feature_values?: Record<
      string,
      string | number | boolean | null
    >;
    feature_contributions?: {
      feature: string;
      value?: string | number | boolean | null;
      contribution: number;
      direction: string;
    }[];
    top_risk_factors?: {
      feature: string;
      value?: string | number | boolean | null;
      contribution: number;
      direction: string;
    }[];
    risk_reducing_factors?: {
      feature: string;
      value?: string | number | boolean | null;
      contribution: number;
      direction: string;
    }[];
  };

  regression: {
    predicted_arrival_delay_minutes: number;
    status: string;
    risk_level: string;
    recommended_action: string;
    raw_prediction?: number;
    feature_contributions?: {
      feature: string;
      value?: string | number | boolean | null;
      contribution: number;
      direction: string;
    }[];
    top_risk_factors?: {
      feature: string;
      value?: string | number | boolean | null;
      contribution: number;
      direction: string;
    }[];
    risk_reducing_factors?: {
      feature: string;
      value?: string | number | boolean | null;
      contribution: number;
      direction: string;
    }[];
  };

  classification_features?: Record<
    string,
    string | number | boolean | null
  >;

  regression_features?: Record<
    string,
    string | number | boolean | null
  >;

  prediction: {
    predicted_arrival_delay_minutes: number;
    delay_probability: number;
    delay_probability_percent: number;
    risk_level: string;
    status: string;
    recommended_action: string;
    prediction_time_ms: number;
  };

  decision: string;

  action: {
    level: string;
    message: string;
    requires_trigger: boolean;
  };

  combined_risk: string;

  reasons: OperationalReason[];

  actual_outcome?: {
    arrival_delay_minutes: number;
    delayed_15: boolean;
    status: string;
    database_delay_status?: string;
    database_delay_category?: string;
  } | null;

  model_contract: {
    classifier: string;
    classifier_target: string;
    classifier_feature_count?: number;
    classifier_features?: string[];

    regressor: string;
    regressor_target: string;
    regressor_feature_count?: number;
    regressor_features?: string[];

    feature_count: number;
    features: string[];

    weather_used: boolean;
    traffic_congestion_feature_used: boolean;
  };

  meta: {
    processing_time_ms: number;
    historical_validation_only: boolean;
  };
};


/* ============================================================
   UI HELPERS
   ============================================================ */

const inputCls =
  "w-full rounded-xl border border-input bg-background/60 px-3 py-2.5 text-sm outline-none transition-shadow focus:shadow-glow";

function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>

      <div className="mt-2">
        {children}
      </div>
    </label>
  );
}

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return String(value);
}

function minuteText(value: unknown): string {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  // Display operational delay values to two decimal places.
  return number.toFixed(2);
}

function percentText(value: unknown): string {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return String(value);
  }

  // Display probability to two decimal places.
  return `${number.toFixed(2)}%`;
}


const EXPECTED_LGB_FEATURES_FALLBACK = [
  "DEPARTURE_DELAY",
  "TAXI_OUT",
  "SCHEDULED_TIME",
  "DISTANCE",
  "SCHEDULED_SPEED",
  "DEP_MIN_OF_DAY",
  "MONTH",
  "DAY",
  "DAY_OF_WEEK",
  "AIRLINE",
  "ORIGIN_AIRPORT",
  "DESTINATION_AIRPORT",
  "ROUTE",
  "AIRLINE_HIST_DELAY",
  "ORIGIN_AIRPORT_HIST_DELAY",
  "DESTINATION_AIRPORT_HIST_DELAY",
  "ROUTE_HIST_DELAY",
];

function persistRebookingContext(
  response: BackendPredictionResponse,
  decision: OperationalDecision,
) {
  const context = {
    decision,
    flight: response.flight,
    prediction: response.prediction,
    reasons: response.reasons,
    response,
    createdAt: new Date().toISOString(),
  };

  try {
    const serialized = JSON.stringify(context);
    localStorage.setItem("flitzz:pendingAction", serialized);
    sessionStorage.setItem("flitzz_prediction", serialized);
  } catch {
    // Navigation can continue even when browser storage is unavailable.
  }
}

/* ============================================================
   MODEL RESULT HELPERS
   ============================================================ */

function featureLabel(feature: string): string {
  const labels: Record<string, string> = {
    airline: "Airline",
    origin_airport: "Origin airport",
    destination_airport: "Destination airport",
    departure_hour: "Departure hour",
    departure_period: "Departure period",
    day_of_week: "Day of week",
    month: "Month",
    season: "Season",
    distance_miles: "Distance",
    route_average_delay_minutes: "Route historical delay",
    route_delay_rate: "Route delay rate",
    route_previous_flights: "Route previous flights",
    route_previous_delays: "Route previous delays",
    airline_average_delay_minutes: "Airline historical delay",
    airline_delay_rate: "Airline delay rate",
    airline_previous_flights: "Airline previous flights",
    airline_previous_delays: "Airline previous delays",
    route_flights_1h: "Route traffic — previous hour",
    route_flights_3h: "Route traffic — previous 3 hours",
    origin_flights_1h: "Origin traffic — previous hour",
    destination_flights_1h: "Destination traffic — previous hour",
    route_congestion_ratio: "Route congestion",
    origin_congestion_ratio: "Origin congestion",
    destination_congestion_ratio: "Destination congestion",

    DEPARTURE_DELAY: "Departure delay",
    TAXI_OUT: "Taxi-out",
    SCHEDULED_TIME: "Scheduled flight time",
    DISTANCE: "Distance",
    SCHEDULED_SPEED: "Scheduled speed",
    DEP_MIN_OF_DAY: "Departure time of day",
    MONTH: "Month",
    DAY: "Day",
    DAY_OF_WEEK: "Day of week",
    AIRLINE: "Airline",
    ORIGIN_AIRPORT: "Origin airport",
    DESTINATION_AIRPORT: "Destination airport",
    ROUTE: "Route",
    AIRLINE_HIST_DELAY: "Airline historical delay",
    ORIGIN_AIRPORT_HIST_DELAY: "Origin historical delay",
    DESTINATION_AIRPORT_HIST_DELAY: "Destination historical delay",
    ROUTE_HIST_DELAY: "Route historical delay",
  };

  return (
    labels[feature] ||
    feature
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase())
  );
}

function isCongestionFeature(feature: string): boolean {
  return feature.toLowerCase().includes("congestion");
}

function compactFeatureLabel(feature: string): string {
  return featureLabel(feature)
    .replace(/\s+/g, " ")
    .trim();
}

function featureValueText(feature: string, value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const numericValue = Number(value);

  if (isCongestionFeature(feature) && Number.isFinite(numericValue)) {
    return numericValue.toFixed(2);
  }

  if (
    feature.toLowerCase().includes("delay") ||
    feature.toLowerCase().includes("taxi")
  ) {
    if (Number.isFinite(numericValue)) {
      return `${numericValue.toFixed(2)} min`;
    }
  }

  if (
    feature.toLowerCase().includes("flights_1h") ||
    feature.toLowerCase().includes("flights_3h")
  ) {
    if (Number.isFinite(numericValue)) {
      return `${Math.round(numericValue)} flights`;
    }
  }

  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }

  return String(value);
}

function congestionLevel(value: unknown): string {
  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "UNKNOWN";
  }

  if (number >= 1) return "HIGH";
  if (number >= 0.5) return "MODERATE";
  return "LOW";
}

function riskBadgeClass(level: string): string {
  const normalized = level.toUpperCase();

  if (normalized === "VERY_HIGH" || normalized === "CRITICAL") {
    return "border-destructive/40 bg-destructive/10 text-destructive";
  }

  if (
    normalized === "HIGH" ||
    normalized === "MODERATE" ||
    normalized === "MEDIUM"
  ) {
    return "border-amber-400/30 bg-amber-400/10 text-amber-300";
  }

  return "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";
}

function ModelFeatureCard({
  feature,
  value,
  contribution,
  maxContribution,
}: {
  feature: string;
  value: unknown;
  contribution?: number;
  maxContribution?: number;
}) {
  const positive = Number(contribution || 0) > 0;
  const negative = Number(contribution || 0) < 0;
  const magnitude = Math.abs(Number(contribution || 0));

  const width =
    maxContribution && maxContribution > 0
      ? Math.min((magnitude / maxContribution) * 100, 100)
      : 0;

  const congestion = isCongestionFeature(feature);
  const congestionRisk = congestion ? congestionLevel(value) : null;

  return (
    <div className="rounded-2xl border border-border/70 bg-background/20 p-4 transition-all duration-300 hover:-translate-y-0.5 hover:bg-background/30">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {featureLabel(feature)}
          </p>

          <p className="mt-1 text-lg font-bold break-words">
            {featureValueText(feature, value)}
          </p>
        </div>

        {congestion && (
          <span
            className={`shrink-0 rounded-full border px-2 py-1 text-[9px] font-bold uppercase tracking-wider ${riskBadgeClass(
              congestionRisk || "UNKNOWN",
            )}`}
          >
            {congestionRisk}
          </span>
        )}
      </div>

      {contribution !== undefined && (
        <div className="mt-3">
          <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
            <span>
              {positive
                ? "Increases delay risk"
                : negative
                  ? "Reduces delay risk"
                  : "Neutral signal"}
            </span>

            <span className="font-semibold">
              {contribution > 0 ? "+" : ""}
              {contribution.toFixed(3)}
            </span>
          </div>

          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                positive
                  ? "bg-destructive"
                  : negative
                    ? "bg-emerald-400"
                    : "bg-muted-foreground"
              }`}
              style={{ width: `${width}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}


function generateShapExplanation(
  classification: BackendPredictionResponse["classification"],
): string {
  const probability = Number(
    classification.delay_probability_percent || 0,
  );

  const riskFactors = (
    classification.top_risk_factors?.length
      ? classification.top_risk_factors
      : (classification.feature_contributions || [])
          .filter((item) => item.contribution > 0)
  ).slice(0, 3);

  const reducingFactors = (
    classification.risk_reducing_factors || []
  ).slice(0, 2);

  const riskLabel =
    classification.probability_risk
      ?.toLowerCase()
      .replaceAll("_", " ") || "current";

  if (!riskFactors.length) {
    return `The model estimates a ${probability.toFixed(
      1,
    )}% probability of a 15+ minute delay based on the available operational flight signals.`;
  }

  const names = riskFactors.map((item) => featureLabel(item.feature));

  let mainFactors = "";
  if (names.length === 1) {
    mainFactors = names[0];
  } else if (names.length === 2) {
    mainFactors = `${names[0]} and ${names[1]}`;
  } else {
    mainFactors = `${names[0]}, ${names[1]}, and ${names[2]}`;
  }

  let explanation =
    `The flight currently has a ${riskLabel} likelihood of delay. ` +
    `The strongest factors increasing the model's delay risk are ${mainFactors}. `;

  if (reducingFactors.length > 0) {
    const reducingNames = reducingFactors.map((item) =>
      featureLabel(item.feature),
    );

    const reducingText =
      reducingNames.length === 1
        ? reducingNames[0]
        : `${reducingNames[0]} and ${reducingNames[1]}`;

    explanation +=
      `Factors such as ${reducingText} are helping reduce the overall risk. `;
  }

  explanation +=
    `Combining these signals, the XGBoost classifier estimates a ` +
    `${probability.toFixed(1)}% probability of a 15+ minute delay.`;

  return explanation;
}


const GLOBAL_NETWORK_ROUTES = [
  { origin: "LAX", destination: "JFK" },
  { origin: "SFO", destination: "LHR" },
  { origin: "SEA", destination: "NRT" },
  { origin: "ATL", destination: "CDG" },
  { origin: "MIA", destination: "GRU" },
  { origin: "DFW", destination: "DEL" },
  { origin: "LHR", destination: "DXB" },
  { origin: "SIN", destination: "SYD" },
];

const NETWORK_FLIGHT_PATHS = [
  { d: "M 8 55 Q 28 34 48 42", dur: "7s", begin: "0s" },
  { d: "M 18 38 Q 42 18 69 25", dur: "9s", begin: "-2s" },
  { d: "M 26 62 Q 44 45 58 35", dur: "8s", begin: "-4s" },
  { d: "M 42 24 Q 55 38 82 31", dur: "10s", begin: "-1s" },
  { d: "M 53 52 Q 67 43 91 57", dur: "8.5s", begin: "-5s" },
  { d: "M 61 30 Q 73 48 96 38", dur: "9.5s", begin: "-3s" },
  { d: "M 12 70 Q 36 57 73 68", dur: "11s", begin: "-6s" },
  { d: "M 35 18 Q 60 10 88 20", dur: "7.5s", begin: "-1.5s" },
];

function GlobalFlightTrafficOverlay() {
  return (
    <div className="pointer-events-none absolute inset-0 z-10">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="h-full w-full"
        aria-hidden="true"
      >
        {NETWORK_FLIGHT_PATHS.map((flight, index) => (
          <g key={index}>
            <path
              id={`flitzz-network-path-${index}`}
              d={flight.d}
              fill="none"
              stroke="white"
              strokeWidth="0.22"
              strokeDasharray="1.2 1.5"
              vectorEffect="non-scaling-stroke"
              opacity="0.42"
            />
            <circle r="0.75" fill="white">
              <animateMotion
                dur={flight.dur}
                begin={flight.begin}
                repeatCount="indefinite"
                rotate="auto"
              >
                <mpath href={`#flitzz-network-path-${index}`} />
              </animateMotion>
            </circle>
          </g>
        ))}
      </svg>
    </div>
  );
}

function XGBoostClassificationCard({
  classification,
}: {
  classification: BackendPredictionResponse["classification"];
}) {
  const probability = Number(
    classification.delay_probability_percent || 0,
  );

  const topFactors = (
    classification.top_risk_factors?.length
      ? classification.top_risk_factors
      : (classification.feature_contributions || [])
          .filter((item) => item.contribution > 0)
  ).slice(0, 3);

  const reducingFactors = (
    classification.risk_reducing_factors || []
  ).slice(0, 2);

  return (
    <div className="rounded-3xl border border-border/70 bg-background/30 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              XGBoost classification
            </p>
          </div>

          <h3 className="mt-2 text-xl font-bold">
            Probability of 15+ minute delay
          </h3>

          <p className="mt-1 text-sm text-muted-foreground">
            Classification model output and the strongest contributing signals.
          </p>
        </div>

        <span
          className={`rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider ${riskBadgeClass(
            classification.probability_risk,
          )}`}
        >
          {classification.probability_risk.replaceAll("_", " ")} risk
        </span>
      </div>

      {/* PROBABILITY — explicitly filled using a solid visible color */}
      <div className="mt-6 grid gap-5 md:grid-cols-[1fr_180px] md:items-center">
        <div>
          <div className="h-4 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-1000 ease-out"
              style={{
                width: `${Math.min(Math.max(probability, 0), 100)}%`,
              }}
            />
          </div>

          <div className="mt-2 flex justify-between text-[10px] font-semibold text-muted-foreground">
            <span>0%</span>
            <span>
              threshold{" "}
              {Number(
                classification.classification_threshold ?? 0.5,
              ) * 100}%
            </span>
            <span>100%</span>
          </div>
        </div>

        <div className="rounded-2xl border border-border/70 bg-background/30 p-4 text-center">
          <p className="text-5xl font-extrabold tracking-tight tabular-nums">
            {probability.toFixed(2)}%
          </p>
          <p className="mt-1 text-xs font-semibold text-muted-foreground">
            delay probability
          </p>
        </div>
      </div>

      {/* ============================================================
          XGBOOST — TOP PREDICTION FEATURES + SHAP
      ============================================================ */}
      <div className="mt-6 rounded-2xl border border-primary/20 bg-primary/5 p-5">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-primary">
            Prediction features
          </p>
          <h4 className="mt-1 text-lg font-extrabold">
            What features drive the delay probability?
          </h4>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            XGBoost evaluates the <strong className="font-extrabold text-foreground">classification feature set</strong>
            and estimates the probability of a delay of <strong className="font-extrabold text-foreground">15+ minutes</strong>.
          </p>
        </div>

        {topFactors.length > 0 ? (
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {topFactors.slice(0, 3).map((factor, index) => (
              <div
                key={`${factor.feature}-xg-feature-${index}`}
                className="rounded-xl border border-border/70 bg-background/30 p-4"
              >
                <p className="text-[10px] font-extrabold uppercase tracking-wider text-primary">
                  Feature {index + 1}
                </p>
                <p className="mt-2 text-sm font-extrabold text-foreground">
                  {compactFeatureLabel(factor.feature)}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Input value:{" "}
                  <strong className="font-extrabold text-foreground">
                    {featureValueText(factor.feature, factor.value)}
                  </strong>
                </p>
              </div>
            ))}
          </div>
        ) : null}

        <div className="mt-6">
          <p className="text-sm font-extrabold text-foreground">
            SHAP explanation
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            These are the <strong className="font-extrabold text-foreground">top three signals</strong> behind the classification probability.
          </p>

          <ul className="mt-4 space-y-3">
            {topFactors.length > 0 ? (
              topFactors.slice(0, 3).map((factor, index) => (
                <li
                  key={`${factor.feature}-xg-shap-${index}`}
                  className="flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5 p-3.5"
                >
                  <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-destructive/15 text-[10px] font-extrabold text-destructive">
                    {index + 1}
                  </span>
                  <p className="text-sm leading-6 text-foreground">
                    <strong className="font-extrabold">
                      {compactFeatureLabel(factor.feature)}
                    </strong>{" "}
                    has a value of{" "}
                    <strong className="font-extrabold">
                      {featureValueText(factor.feature, factor.value)}
                    </strong>{" "}
                    and contributes{" "}
                    <strong className="font-extrabold text-destructive">
                      +{Number(factor.contribution || 0).toFixed(3)}
                    </strong>{" "}
                    to the model,{" "}
                    <strong className="font-extrabold">
                      increasing the probability of a 15+ minute delay.
                    </strong>
                  </p>
                </li>
              ))
            ) : (
              <li className="rounded-xl border border-border/70 bg-background/20 p-4 text-sm text-muted-foreground">
                No individual SHAP contribution signals were returned by the classifier.
              </li>
            )}
          </ul>

          {reducingFactors.length > 0 && (
            <div className="mt-5">
              <p className="text-sm font-extrabold text-foreground">
                Risk-reducing signals
              </p>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-muted-foreground">
                {reducingFactors.slice(0, 3).map((factor, index) => (
                  <li key={`${factor.feature}-xg-reduce-${index}`}>
                    • <strong className="font-extrabold text-foreground">
                      {compactFeatureLabel(factor.feature)}
                    </strong>{" "}
                    ({featureValueText(factor.feature, factor.value)}) has a{" "}
                    <strong className="font-extrabold text-emerald-300">
                      {Number(factor.contribution || 0).toFixed(3)}
                    </strong>{" "}
                    SHAP contribution and helps reduce delay risk.
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="mt-5 rounded-xl border border-border/60 bg-background/30 p-4">
          <p className="text-xs font-extrabold uppercase tracking-wider text-primary">
            XGBoost conclusion
          </p>
          <p className="mt-2 text-base leading-7 text-foreground">
            XGBoost estimates a{" "}
            <strong className="font-extrabold">
              {probability.toFixed(2)}% probability of a 15+ minute delay
            </strong>
            . The three highlighted features are the strongest available
            explanation signals for this classification.
          </p>
        </div>
      </div>
    </div>
  );
}

function LightGBMRegressionCard({
  regression,
}: {
  regression: BackendPredictionResponse["regression"];
}) {
  const delay = Number(
    regression.predicted_arrival_delay_minutes || 0,
  );

  const maxDelayBar = 120;
  const delayBarWidth = Math.min(
    Math.max((delay / maxDelayBar) * 100, 0),
    100,
  );

  const regressionRiskFactors = (
    regression.top_risk_factors?.length
      ? regression.top_risk_factors
      : (regression.feature_contributions || [])
          .filter((item) => item.contribution > 0)
  ).slice(0, 4);

  const regressionReducingFactors = (
    regression.risk_reducing_factors || []
  ).slice(0, 3);

  const hasRegressionShap =
    regressionRiskFactors.length > 0 ||
    regressionReducingFactors.length > 0;

  return (
    <div className="rounded-3xl border border-border/70 bg-background/30 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              LightGBM regression
            </p>
          </div>

          <h3 className="mt-2 text-xl font-bold">
            Expected arrival delay
          </h3>

          <p className="mt-1 text-sm text-muted-foreground">
            Regression prediction followed by the strongest SHAP signals.
          </p>
        </div>

        <span
          className={`rounded-full border px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider ${riskBadgeClass(
            regression.risk_level,
          )}`}
        >
          {regression.risk_level} risk
        </span>
      </div>

      {/* ============================================================
          LIGHTGBM DELAY BAR — FIRST
      ============================================================ */}
      <div className="mt-6 grid gap-5 md:grid-cols-[1fr_180px] md:items-center">
        <div>
          <div className="flex items-center justify-between text-[10px] font-extrabold uppercase tracking-wider text-muted-foreground">
            <span>0 min</span>
            <span>Expected arrival delay</span>
            <span>{maxDelayBar} min+</span>
          </div>

          <div className="mt-2 h-4 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-destructive transition-[width] duration-1000 ease-out"
              style={{ width: `${delayBarWidth}%` }}
            />
          </div>

          <div className="mt-2 flex justify-between text-[10px] font-semibold text-muted-foreground">
            <span>Low</span>
            <span>Higher predicted delay</span>
          </div>
        </div>

        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-4 text-center">
          <p className="text-5xl font-extrabold tracking-tight tabular-nums">
            {delay.toFixed(2)}
          </p>
          <p className="mt-1 text-xs font-extrabold text-muted-foreground">
            predicted delay · min
          </p>
        </div>
      </div>

      {/* ============================================================
          LIGHTGBM — TOP PREDICTION FEATURES + SHAP
      ============================================================ */}
      <div className="mt-6 rounded-2xl border border-primary/20 bg-primary/5 p-5">
        <div>
          <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-primary">
            Prediction features
          </p>
          <h4 className="mt-1 text-lg font-extrabold">
            What features drive the predicted delay?
          </h4>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            The model uses the flight's <strong className="font-extrabold text-foreground">17 trained features</strong>.
            The strongest available contribution signals are highlighted below.
          </p>
        </div>

        {regressionRiskFactors.length > 0 ? (
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {regressionRiskFactors.slice(0, 3).map((factor, index) => (
              <div
                key={`${factor.feature}-lg-feature-${index}`}
                className="rounded-xl border border-border/70 bg-background/30 p-4"
              >
                <p className="text-[10px] font-extrabold uppercase tracking-wider text-primary">
                  Feature {index + 1}
                </p>
                <p className="mt-2 text-sm font-extrabold text-foreground">
                  {compactFeatureLabel(factor.feature)}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Input value:{" "}
                  <strong className="font-extrabold text-foreground">
                    {featureValueText(factor.feature, factor.value)}
                  </strong>
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-xl border border-border/70 bg-background/20 p-4 text-sm text-muted-foreground">
            The trained 17-feature schema is used by LightGBM. Individual
            contribution signals are not currently returned by the API.
          </div>
        )}

        <div className="mt-6">
          <p className="text-sm font-extrabold text-foreground">
            SHAP explanation
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            The top signals explain <strong className="font-extrabold text-foreground">why the model predicts this number of minutes</strong>.
          </p>

          {hasRegressionShap ? (
            <ul className="mt-4 space-y-3">
              {regressionRiskFactors.slice(0, 3).map((factor, index) => (
                <li
                  key={`${factor.feature}-lg-shap-${index}`}
                  className="flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5 p-3.5"
                >
                  <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-destructive/15 text-[10px] font-extrabold text-destructive">
                    {index + 1}
                  </span>
                  <p className="text-sm leading-6 text-foreground">
                    <strong className="font-extrabold">
                      {compactFeatureLabel(factor.feature)}
                    </strong>{" "}
                    has a value of{" "}
                    <strong className="font-extrabold">
                      {featureValueText(factor.feature, factor.value)}
                    </strong>{" "}
                    and contributes{" "}
                    <strong className="font-extrabold text-destructive">
                      {Number(factor.contribution || 0) >= 0 ? "+" : ""}
                      {Number(factor.contribution || 0).toFixed(3)}
                    </strong>{" "}
                    to the prediction,{" "}
                    <strong className="font-extrabold">
                      {Number(factor.contribution || 0) >= 0
                        ? "pushing the expected delay higher."
                        : "pulling the expected delay lower."}
                    </strong>
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <ul className="mt-4 space-y-2 text-sm leading-6 text-muted-foreground">
              <li>
                • <strong className="font-extrabold text-foreground">17 trained features</strong> are used by the LightGBM model.
              </li>
              <li>
                • The <strong className="font-extrabold text-foreground">predicted arrival delay</strong> is the model's direct regression output.
              </li>
              <li>
                • Individual <strong className="font-extrabold text-foreground">LightGBM SHAP contributions</strong> need to be returned by the backend to provide feature-level explanations.
              </li>
            </ul>
          )}
        </div>

        <div className="mt-5 rounded-xl border border-border/60 bg-background/30 p-4">
          <p className="text-xs font-extrabold uppercase tracking-wider text-primary">
            LightGBM conclusion
          </p>
          <p className="mt-2 text-base leading-7 text-foreground">
            LightGBM predicts an{" "}
            <strong className="font-extrabold">
              expected arrival delay of {delay.toFixed(2)} minutes
            </strong>
            . The highlighted features and SHAP signals explain the strongest
            available drivers of that prediction.
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Model status
          </p>
          <p className="mt-2 text-lg font-extrabold break-words">
            {regression.status}
          </p>
        </div>

        <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Recommended action
          </p>
          <p className="mt-2 text-sm font-extrabold leading-5">
            {regression.recommended_action.replaceAll("_", " ")}
          </p>
        </div>

        <div className="rounded-2xl border border-border/70 bg-background/20 p-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
            Prediction type
          </p>
          <p className="mt-2 text-sm font-extrabold leading-5">
            Direct duration prediction
          </p>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   DECISION UI
   ============================================================ */

type OperationalDecision =
  | "NORMAL_WAIT"
  | "MANUAL_ACTION"
  | "AUTOMATIC_ACTION";

function DecisionBadge({
  decision,
}: {
  decision: OperationalDecision;
}) {
  const styles =
    decision === "AUTOMATIC_ACTION"
      ? "border-destructive/40 bg-destructive/10 text-destructive"
      : decision === "MANUAL_ACTION"
        ? "border-amber-400/30 bg-amber-400/10 text-amber-300"
        : "border-emerald-400/30 bg-emerald-400/10 text-emerald-300";

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold ${styles}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />

      {decision === "AUTOMATIC_ACTION"
        ? "Automatic action"
        : decision === "MANUAL_ACTION"
          ? "Manual action"
          : "Normal"}
    </span>
  );
}


/* ============================================================
   PREDICT PAGE
   ============================================================ */

function Predict() {
  const navigate = useNavigate();

  const {
    isAuthenticated,
  } = useAuth();

  const [flightId, setFlightId] = useState("");

  const [loading, setLoading] =
    useState(false);

  const [backendResponse, setBackendResponse] =
    useState<BackendPredictionResponse | null>(
      null,
    );

  const [error, setError] =
    useState<string | null>(null);


  /* ==========================================================
     AUTH
     ========================================================== */

  useEffect(() => {
    if (!isAuthenticated) {
      navigate({
        to: "/login",
      });
    }
  }, [
    isAuthenticated,
    navigate,
  ]);

  if (!isAuthenticated) {
    return null;
  }


  /* ==========================================================
     SUBMIT
     ========================================================== */

  async function submit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    const id = flightId.trim();

    if (!id || !/^\d+$/.test(id)) {
      setError("Enter a valid flight ID.");
      return;
    }

    if (loading) {
      return;
    }

    setLoading(true);
    setBackendResponse(null);
    setError(null);

    try {
      const payload = {
        flight_key: id,
      };

      const response =
        await fetch(
          `${API_URL}/predict`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
              Accept:
                "application/json",
            },

            body:
              JSON.stringify(
                payload,
              ),
          },
        );

      let data:
        BackendPredictionResponse;

      try {
        data =
          await response.json();
      } catch {
        throw new Error(
          "Backend returned invalid JSON.",
        );
      }

      if (!response.ok) {
        const detail =
          (
            data as unknown as {
              detail?: string | {
                loc?: unknown[];
                msg?: string;
              }[];
            }
          )?.detail;

        const message =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail
                  .map((item) => item.msg || "Validation error")
                  .join("; ")
              : undefined;

        throw new Error(
          message ||
            `Prediction failed with HTTP ${response.status}.`,
        );
      }

      if (!data.success) {
        throw new Error(
          "Backend returned success=false.",
        );
      }

      setBackendResponse(data);

      /* ------------------------------------------------------
         Save complete prediction for reports / ops pages.
      ------------------------------------------------------ */

      try {
        localStorage.setItem(
          "flitzz:lastPrediction",
          JSON.stringify({
            request: payload,
            response: data,
            createdAt:
              new Date().toISOString(),
          }),
        );
      } catch {
        // Prediction itself succeeded.
      }


      /* ------------------------------------------------------
         Existing prediction-store compatibility.
      ------------------------------------------------------ */

      try {
        savePrediction({
          probability:
            Number(
              data.classification
                .delay_probability,
            ),

          level:
            String(
              data.combined_risk ||
                data.regression.risk_level ||
                "LOW",
            ).toLowerCase(),

          expectedDelayMin:
            Number(
              data.regression
                .predicted_arrival_delay_minutes,
            ),

          confidence:
            Number(
              data.classification
                .delay_probability_percent,
            ),

          factors:
            data.reasons.map(
              (reason) =>
                reason.title,
            ),
        } as any);
      } catch {
        // Keep UI prediction successful even if the legacy store fails.
      }
    } catch (err) {
      console.error(
        "FLITZZ prediction error:",
        err,
      );

      setError(
        err instanceof Error
          ? err.message
          : "Unable to connect to the FLITZZ prediction backend.",
      );
    } finally {
      setLoading(false);
    }
  }


  /* ==========================================================
     RESULT
     ========================================================== */

  const prediction =
    backendResponse?.prediction;

  const predictedDelay =
    prediction
      ? Number(
          prediction.predicted_arrival_delay_minutes,
        )
      : null;

  /* ==========================================================
     OPERATIONAL ACTION RULES

     < 15 min   → NORMAL
     15–29.99   → MANUAL ACTION
     >= 30 min  → AUTOMATIC ACTION
  ========================================================== */
  const decision: OperationalDecision =
    predictedDelay === null || !Number.isFinite(predictedDelay)
      ? "NORMAL_WAIT"
      : predictedDelay < 15
        ? "NORMAL_WAIT"
        : predictedDelay < 30
          ? "MANUAL_ACTION"
          : "AUTOMATIC_ACTION";

  const requiresRebook =
    predictedDelay !== null &&
    Number.isFinite(predictedDelay) &&
    predictedDelay >= 15;


  /* ============================================================
     RENDER
     ============================================================ */

  return (
    <PageShell
      eyebrow="Operational prediction"
      title="Predict Flight Delay"
      description="Enter only a flight ID. FLITZZ retrieves the real flight from PostgreSQL, runs the XGBoost classifier and the separate LightGBM regression model, and reveals the prediction below the live global route map."
    >
      {error && (
        <div className="mb-6 rounded-2xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <p className="font-semibold">
            Prediction failed
          </p>
          <p className="mt-1">
            {error}
          </p>
          <p className="mt-2 text-xs opacity-80">
            Check that PostgreSQL is running, the flight exists,
            and FastAPI is running on {API_URL}.
          </p>
        </div>
      )}

      {/* ======================================================
          INPUT LEFT + GLOBAL MAP RIGHT
      ====================================================== */}

      <div className="grid items-stretch gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">

        <Reveal>
          <GlassCard className="h-full">
            <form
              onSubmit={submit}
              className="flex h-full flex-col gap-5"
            >
              <div>
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-primary" />
                  <p className="text-sm font-semibold">
                    Flight lookup
                  </p>
                </div>

                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Enter only the unique flight ID.
                  All flight and model data is fetched dynamically
                  from PostgreSQL.
                </p>
              </div>

              <Field label="Flight ID">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

                  <input
                    type="text"
                    inputMode="numeric"
                    value={flightId}
                    onChange={(event) =>
                      setFlightId(
                        event.target.value.replace(/\D/g, ""),
                      )
                    }
                    placeholder="e.g. 123456"
                    className={`${inputCls} pl-10`}
                    autoComplete="off"
                    required
                  />
                </div>
              </Field>

              <div className="rounded-2xl border border-border/70 bg-background/30 p-4">
                <div className="flex items-center gap-2">
                  <Activity className="h-4 w-4 text-primary" />
                  <p className="text-sm font-semibold">
                    Live model analysis
                  </p>
                </div>

                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  XGBoost estimates the probability of a 15+ minute
                  delay. The separate LightGBM model predicts the
                  expected delay duration.
                </p>
              </div>

              <div className="mt-auto">
                <button
                  type="submit"
                  disabled={
                    loading ||
                    !flightId.trim()
                  }
                  className="bg-brand inline-flex w-full items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-primary-foreground shadow-glow transition-transform duration-300 hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4" />
                  )}

                  {loading
                    ? "Analyzing flight…"
                    : "Predict delay"}
                </button>
              </div>
            </form>
          </GlassCard>
        </Reveal>


        <Reveal delay={80}>
          <GlassCard className="h-full overflow-hidden p-0">
            <div className="relative min-h-[500px]">

              <div className="absolute left-5 right-5 top-5 z-20 flex flex-wrap items-start justify-between gap-3">
                <div className="rounded-2xl border border-border/70 bg-background/70 px-4 py-3 backdrop-blur-xl">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-primary">
                    FLITZZ global network
                  </p>

                  <h2 className="mt-1 text-lg font-bold">
                    Interactive Global Route Map
                  </h2>

                  <p className="mt-1 text-xs text-muted-foreground">
                    {loading
                      ? `Analyzing flight #${flightId || "—"}`
                      : backendResponse
                        ? `8 live routes · ${backendResponse.flight.origin_airport} → ${backendResponse.flight.destination_airport}`
                        : "8 live routes · multi-direction network"}
                  </p>
                </div>

                <div className="rounded-full border border-border/70 bg-background/70 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground backdrop-blur-xl">
                  {loading
                    ? "Prediction in progress"
                    : "Network live"}
                </div>
              </div>

              <FlightMap
                routes={GLOBAL_NETWORK_ROUTES}
                height={520}
              />

              <GlobalFlightTrafficOverlay />

              {loading && (
                <div className="pointer-events-none absolute inset-0 z-10 flex items-end justify-center bg-gradient-to-t from-background/70 via-transparent to-transparent p-6">
                  <div className="flex items-center gap-3 rounded-full border border-primary/30 bg-background/75 px-5 py-3 shadow-glow backdrop-blur-xl">
                    <span className="relative flex h-3 w-3">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-60" />
                      <span className="relative inline-flex h-3 w-3 rounded-full bg-primary" />
                    </span>

                    <span className="text-xs font-semibold">
                      PostgreSQL → XGBoost → LightGBM
                    </span>
                  </div>
                </div>
              )}
            </div>
          </GlassCard>
        </Reveal>
      </div>


      {/* ======================================================
          RESULTS — REVEAL BELOW THE MAP
      ====================================================== */}

      {backendResponse && (
        <div className="mt-6">
            <GlassCard>

              <div className="mb-6 flex flex-wrap items-start justify-between gap-4 border-b border-border/60 pb-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-primary">
                    Prediction result
                  </p>

                  <h2 className="mt-1 text-2xl font-bold">
                    Flight {backendResponse.flight.flight_id}
                  </h2>

                  <p className="mt-1 text-sm text-muted-foreground">
                    {backendResponse.flight.origin_airport}
                    {" → "}
                    {backendResponse.flight.destination_airport}
                    {" · "}
                    {backendResponse.flight.flight_number}
                    {" · "}
                    {backendResponse.flight.airline_name ||
                      backendResponse.flight.airline}
                  </p>
                </div>

                {requiresRebook && (
                  <a
                    href={`/rebook?flight_id=${backendResponse.flight.flight_id}`}
                    onClick={() =>
                      persistRebookingContext(
                        backendResponse,
                        decision,
                      )
                    }
                    className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-brand px-5 py-3 text-sm font-extrabold text-primary-foreground shadow-glow transition-transform hover:scale-[1.02]"
                  >
                    {decision === "AUTOMATIC_ACTION"
                      ? "Rebook Flight"
                      : "Review & Rebook"}
                    <ArrowRight className="h-4 w-4" />
                  </a>
                )}
              </div>


              {/* RESULT */}

              {!loading &&
                backendResponse && (
                  <div className="grid gap-6">

                    {/* FLIGHT HEADER */}

                    <div className="flex flex-wrap items-start justify-between gap-4">

                      <div>

                        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          Flight
                        </p>

                        <h2 className="mt-1 text-2xl font-bold">
                          {
                            backendResponse.flight
                              .origin_airport
                          }

                          {" → "}

                          {
                            backendResponse.flight
                              .destination_airport
                          }
                        </h2>

                        <p className="mt-1 text-sm text-muted-foreground">
                          {
                            backendResponse.flight
                              .flight_number
                          }

                          {" · "}

                          {
                            backendResponse.flight
                              .airline_name ||
                            backendResponse.flight
                              .airline
                          }

                          {" · ID "}

                          {
                            backendResponse.flight
                              .flight_id
                          }
                        </p>

                      </div>

                      <DecisionBadge
                        decision={
                          decision
                        }
                      />

                    </div>


                    {/* ==================================================
                        SEPARATE MODEL RESULTS
                    ================================================== */}

                    <div className="grid gap-5">
                      {/* LightGBM regression first */}
                      <LightGBMRegressionCard
                        regression={
                          backendResponse.regression
                        }
                      />

                      {/* XGBoost classification second */}
                      <XGBoostClassificationCard
                        classification={
                          backendResponse.classification
                        }
                      />
                    </div>


                    {/* ==================================================
                        OPERATIONAL ACTION

                        One decision + one action button.
                        The action is driven directly by the LightGBM
                        predicted arrival delay.
                    ================================================== */}
                    <div
                      className={`rounded-3xl border p-6 ${
                        decision === "AUTOMATIC_ACTION"
                          ? "border-destructive/40 bg-destructive/10"
                          : decision === "MANUAL_ACTION"
                            ? "border-amber-400/30 bg-amber-400/10"
                            : "border-emerald-400/30 bg-emerald-400/10"
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-5">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-xs font-extrabold uppercase tracking-[0.16em] text-primary">
                              Operational action
                            </p>
                            <DecisionBadge decision={decision} />
                          </div>

                          <h3 className="mt-3 text-xl font-extrabold">
                            {decision === "AUTOMATIC_ACTION"
                              ? "Automatic rebooking recommended"
                              : decision === "MANUAL_ACTION"
                                ? "Manual rebooking review required"
                                : "No rebooking action required"}
                          </h3>

                          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
                            LightGBM predicts an expected arrival delay of{" "}
                            <strong className="font-extrabold text-foreground">
                              {predictedDelay !== null
                                ? `${minuteText(predictedDelay)} min`
                                : "—"}
                            </strong>.{" "}
                            {decision === "AUTOMATIC_ACTION"
                              ? "The prediction is at or above the 30-minute automation threshold."
                              : decision === "MANUAL_ACTION"
                                ? "The prediction is between 15 and 30 minutes, so an operations review is required before rebooking."
                                : "The prediction is below the 15-minute intervention threshold, so the flight can continue under normal monitoring."}
                          </p>
                        </div>

                        {requiresRebook && (
                          <a
                            href={`/rebook?flight_id=${backendResponse.flight.flight_id}`}
                            onClick={() =>
                              persistRebookingContext(
                                backendResponse,
                                decision,
                              )
                            }
                            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-brand px-5 py-3 text-sm font-extrabold text-primary-foreground shadow-glow transition-transform hover:scale-[1.02]"
                          >
                            {decision === "AUTOMATIC_ACTION"
                              ? "Rebook Flight"
                              : "Review & Rebook"}
                            <ArrowRight className="h-4 w-4" />
                          </a>
                        )}
                      </div>

                      <div className="mt-5 grid gap-3 sm:grid-cols-3">
                        <div className="rounded-2xl border border-border/60 bg-background/20 p-4">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                            Decision threshold
                          </p>
                          <p className="mt-2 text-sm font-extrabold">
                            {decision === "AUTOMATIC_ACTION"
                              ? "≥ 30 min"
                              : decision === "MANUAL_ACTION"
                                ? "15–29.99 min"
                                : "< 15 min"}
                          </p>
                        </div>

                        <div className="rounded-2xl border border-border/60 bg-background/20 p-4">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                            Automation policy
                          </p>
                          <p className="mt-2 text-sm font-extrabold">
                            {decision === "AUTOMATIC_ACTION"
                              ? "Automatic intervention"
                              : decision === "MANUAL_ACTION"
                                ? "Human review"
                                : "Continue monitoring"}
                          </p>
                        </div>

                        <div className="rounded-2xl border border-border/60 bg-background/20 p-4">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                            Decision source
                          </p>
                          <p className="mt-2 text-sm font-extrabold">
                            LightGBM predicted delay
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* ACTUAL DB OUTCOME */}

                    {backendResponse.actual_outcome && (
                      <div className="rounded-2xl border border-border/70 bg-background/20 p-5">

                        <div className="flex flex-wrap items-center justify-between gap-3">

                          <div>

                            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              Database actual outcome
                            </p>

                            <p className="mt-1 text-sm text-muted-foreground">
                              Validation only — this value
                              was NOT sent to the ML models.
                            </p>

                          </div>

                          <span className="rounded-full border border-border px-3 py-1 text-xs font-semibold">
                            {
                              backendResponse
                                .actual_outcome
                                .status
                            }
                          </span>

                        </div>

                        <div className="mt-4 grid gap-3 sm:grid-cols-3">

                          <Stat
                            label="Actual arrival delay"
                            value={`${minuteText(
                              backendResponse
                                .actual_outcome
                                .arrival_delay_minutes,
                            )} min`}
                          />

                          <Stat
                            label="Actual delayed ≥15"
                            value={
                              backendResponse
                                .actual_outcome
                                .delayed_15
                                ? "Yes"
                                : "No"
                            }
                          />

                          <Stat
                            label="Prediction vs actual"
                            value={
                              predictedDelay !==
                              null
                                ? `${minuteText(
                                    Math.abs(
                                      predictedDelay -
                                        Number(
                                          backendResponse
                                            .actual_outcome
                                            .arrival_delay_minutes,
                                        ),
                                    ),
                                  )} min error`
                                : "—"
                            }
                          />

                        </div>

                      </div>
                    )}


                    {/* REPORT */}

                    <div className="flex flex-wrap gap-3">

                      <Link
                        to="/reports"
                        className="inline-flex items-center justify-center rounded-full border border-border px-5 py-2.5 text-sm font-semibold transition-colors hover:bg-accent"
                      >
                        View full report
                      </Link>

                    </div>

                  </div>
                )}

            </GlassCard>
        </div>
      )}
    </PageShell>
  );
}

/* ============================================================
   REASON CARD
   ============================================================ */

function ReasonCard({
  reason,
}: {
  reason: OperationalReason;
}) {
  const high =
    reason.severity ===
    "HIGH";

  const moderate =
    reason.severity ===
    "MODERATE";

  return (
    <div className="rounded-2xl border border-border/70 bg-background/20 p-4">

      <div className="flex items-start gap-3">

        <div
          className={`
            mt-1 h-2.5 w-2.5 shrink-0 rounded-full
            ${
              high
                ? "bg-destructive"
                : moderate
                  ? "bg-amber-400"
                  : "bg-emerald-400"
            }
          `}
        />

        <div className="min-w-0 flex-1">

          <div className="flex flex-wrap items-center justify-between gap-2">

            <p className="font-semibold">
              {reason.title}
            </p>

            <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
              {reason.severity}
            </span>

          </div>

          <p className="mt-1 text-sm text-muted-foreground">
            {reason.description}
          </p>

        </div>

      </div>

    </div>
  );
}


/* ============================================================
   STAT
   ============================================================ */

function Stat({
  label,
  value,
}: {
  label: string;
  value: string | number | undefined;
}) {
  return (
    <div className="rounded-2xl border border-border px-4 py-3">

      <p className="text-xs text-muted-foreground">
        {label}
      </p>

      <p className="font-display mt-1 text-lg font-bold break-words">
        {valueText(value)}
      </p>

    </div>
  );
}