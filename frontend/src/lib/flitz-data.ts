export type Airport = {
  code: string;
  name: string;
  city: string;
  lat: number;
  lon: number;
  delayRate: number;
  traffic: number;
};

export const AIRPORTS: Airport[] = [
  {
    code: "ATL",
    name: "Hartsfield–Jackson",
    city: "Atlanta",
    lat: 33.6407,
    lon: -84.4277,
    delayRate: 21.4,
    traffic: 0.94,
  },
  {
    code: "JFK",
    name: "John F. Kennedy Intl",
    city: "New York",
    lat: 40.6413,
    lon: -73.7781,
    delayRate: 28.9,
    traffic: 0.88,
  },
  {
    code: "LAX",
    name: "Los Angeles Intl",
    city: "Los Angeles",
    lat: 33.9416,
    lon: -118.4085,
    delayRate: 24.1,
    traffic: 0.91,
  },
  {
    code: "ORD",
    name: "O'Hare Intl",
    city: "Chicago",
    lat: 41.9742,
    lon: -87.9073,
    delayRate: 31.2,
    traffic: 0.96,
  },
  {
    code: "DFW",
    name: "Dallas/Fort Worth",
    city: "Dallas",
    lat: 32.8998,
    lon: -97.0403,
    delayRate: 19.8,
    traffic: 0.9,
  },
  {
    code: "DEN",
    name: "Denver Intl",
    city: "Denver",
    lat: 39.8561,
    lon: -104.6737,
    delayRate: 22.6,
    traffic: 0.85,
  },
  {
    code: "SFO",
    name: "San Francisco Intl",
    city: "San Francisco",
    lat: 37.6213,
    lon: -122.379,
    delayRate: 30.4,
    traffic: 0.83,
  },
  {
    code: "SEA",
    name: "Seattle–Tacoma",
    city: "Seattle",
    lat: 47.4502,
    lon: -122.3088,
    delayRate: 20.2,
    traffic: 0.74,
  },
  {
    code: "MIA",
    name: "Miami Intl",
    city: "Miami",
    lat: 25.7959,
    lon: -80.287,
    delayRate: 26.3,
    traffic: 0.79,
  },
  {
    code: "BOS",
    name: "Logan Intl",
    city: "Boston",
    lat: 42.3656,
    lon: -71.0096,
    delayRate: 25.5,
    traffic: 0.72,
  },
  {
    code: "LHR",
    name: "Heathrow",
    city: "London",
    lat: 51.47,
    lon: -0.4543,
    delayRate: 27.8,
    traffic: 0.93,
  },
  {
    code: "CDG",
    name: "Charles de Gaulle",
    city: "Paris",
    lat: 49.0097,
    lon: 2.5479,
    delayRate: 24.9,
    traffic: 0.87,
  },
  {
    code: "FRA",
    name: "Frankfurt am Main",
    city: "Frankfurt",
    lat: 50.0379,
    lon: 8.5622,
    delayRate: 23.1,
    traffic: 0.86,
  },
  {
    code: "DXB",
    name: "Dubai Intl",
    city: "Dubai",
    lat: 25.2532,
    lon: 55.3657,
    delayRate: 18.4,
    traffic: 0.95,
  },
  {
    code: "DEL",
    name: "Indira Gandhi Intl",
    city: "Delhi",
    lat: 28.5562,
    lon: 77.1,
    delayRate: 29.6,
    traffic: 0.89,
  },
  {
    code: "BOM",
    name: "Chhatrapati Shivaji",
    city: "Mumbai",
    lat: 19.0896,
    lon: 72.8656,
    delayRate: 32.7,
    traffic: 0.92,
  },
  {
    code: "SIN",
    name: "Changi",
    city: "Singapore",
    lat: 1.3644,
    lon: 103.9915,
    delayRate: 14.2,
    traffic: 0.81,
  },
  {
    code: "HND",
    name: "Haneda",
    city: "Tokyo",
    lat: 35.5494,
    lon: 139.7798,
    delayRate: 12.8,
    traffic: 0.88,
  },
  {
    code: "SYD",
    name: "Kingsford Smith",
    city: "Sydney",
    lat: -33.9399,
    lon: 151.1753,
    delayRate: 21.9,
    traffic: 0.7,
  },
  {
    code: "GRU",
    name: "Guarulhos",
    city: "São Paulo",
    lat: -23.4356,
    lon: -46.4731,
    delayRate: 25.1,
    traffic: 0.76,
  },
];

export const AIRLINES = [
  { code: "AA", name: "American Airlines", onTime: 76.2 },
  { code: "DL", name: "Delta Air Lines", onTime: 82.7 },
  { code: "UA", name: "United Airlines", onTime: 78.4 },
  { code: "BA", name: "British Airways", onTime: 74.9 },
  { code: "EK", name: "Emirates", onTime: 85.1 },
  { code: "SQ", name: "Singapore Airlines", onTime: 88.3 },
  { code: "AI", name: "Air India", onTime: 68.5 },
  { code: "LH", name: "Lufthansa", onTime: 79.6 },
];

export const WEATHER_OPTIONS = [
  { value: "clear", label: "Clear", weight: 0 },
  { value: "cloudy", label: "Cloudy", weight: 0.05 },
  { value: "rain", label: "Rain", weight: 0.16 },
  { value: "snow", label: "Snow", weight: 0.28 },
  { value: "storm", label: "Thunderstorm", weight: 0.34 },
  { value: "fog", label: "Fog / Low visibility", weight: 0.22 },
] as const;

export function airport(code: string): Airport {
  return AIRPORTS.find((a) => a.code === code) ?? AIRPORTS[0]!;
}

export function haversineKm(a: Airport, b: Airport) {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLon = ((b.lon - a.lon) * Math.PI) / 180;
  const la1 = (a.lat * Math.PI) / 180;
  const la2 = (b.lat * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(h)));
}

export type RiskLevel = "Low" | "Medium" | "High";

export type Factor = { label: string; impact: number; detail: string };

export type PredictionInput = {
  airline: string;
  origin: string;
  destination: string;
  date: string;
  departureTime: string;
  arrivalTime: string;
  distanceKm: number;
  weather: string;
  traffic: number;
};

export type PredictionResult = {
  input: PredictionInput;
  probability: number;
  level: RiskLevel;
  factors: Factor[];
  expectedDelayMin: number;
  confidence: number;
  timestamp: string;
};

export function riskLevel(p: number): RiskLevel {
  if (p < 0.3) return "Low";
  if (p < 0.6) return "Medium";
  return "High";
}

export function riskToken(level: RiskLevel) {
  return level === "Low" ? "risk-low" : level === "Medium" ? "risk-medium" : "risk-high";
}

/** Deterministic, explainable scoring model (client-side surrogate of the trained gradient-boosted model). */
export function predictDelay(input: PredictionInput): PredictionResult {
  const org = airport(input.origin);
  const dst = airport(input.destination);
  const hour = Number(input.departureTime.split(":")[0] ?? 8);
  const month = Number(input.date.split("-")[1] ?? 6);
  const airline = AIRLINES.find((a) => a.code === input.airline) ?? AIRLINES[0]!;
  const weather = WEATHER_OPTIONS.find((w) => w.value === input.weather) ?? WEATHER_OPTIONS[0]!;

  const hourCurve = [
    0.06, 0.04, 0.03, 0.02, 0.03, 0.05, 0.07, 0.1, 0.13, 0.14, 0.15, 0.17, 0.19, 0.21, 0.24, 0.27,
    0.3, 0.32, 0.33, 0.31, 0.27, 0.22, 0.16, 0.1,
  ];
  const seasonCurve = [0.2, 0.17, 0.12, 0.09, 0.1, 0.16, 0.19, 0.18, 0.1, 0.09, 0.13, 0.22];

  const parts: Factor[] = [
    {
      label: "Departure hour",
      impact: hourCurve[Math.min(23, Math.max(0, hour))]!,
      detail: `${String(hour).padStart(2, "0")}:00 slot — congestion cascades build through the day`,
    },
    {
      label: "Weather at origin",
      impact: weather.weight,
      detail: `${weather.label} conditions at ${org.code}`,
    },
    {
      label: "Airport congestion",
      impact: (org.traffic * 0.18 + dst.traffic * 0.1) * (0.6 + input.traffic * 0.8),
      detail: `${org.code} traffic index ${org.traffic.toFixed(2)}, ${dst.code} ${dst.traffic.toFixed(2)}`,
    },
    {
      label: "Historical route delay",
      impact: ((org.delayRate + dst.delayRate) / 2 / 100) * 0.55,
      detail: `${org.code}→${dst.code} historical delay rate ${(
        (org.delayRate + dst.delayRate) /
        2
      ).toFixed(1)}%`,
    },
    {
      label: "Carrier reliability",
      impact: ((100 - airline.onTime) / 100) * 0.42,
      detail: `${airline.name} on-time performance ${airline.onTime}%`,
    },
    {
      label: "Seasonality",
      impact: seasonCurve[Math.min(11, Math.max(0, month - 1))]!,
      detail: `Month ${month} network-wide seasonal pressure`,
    },
    {
      label: "Stage length",
      impact: input.distanceKm > 4000 ? 0.11 : input.distanceKm < 700 ? 0.14 : 0.05,
      detail: `${input.distanceKm.toLocaleString()} km sector`,
    },
  ];

  const raw = parts.reduce((s, p) => s + p.impact, 0) - 1.05;
  const probability = Math.min(0.97, Math.max(0.03, 1 / (1 + Math.exp(-raw * 2.4))));
  const total = parts.reduce((s, p) => s + p.impact, 0) || 1;
  const factors = parts
    .map((p) => ({ ...p, impact: Math.round((p.impact / total) * 1000) / 10 }))
    .sort((a, b) => b.impact - a.impact);

  return {
    input,
    probability,
    level: riskLevel(probability),
    factors,
    expectedDelayMin: Math.round(probability * 78 + 4),
    confidence: Math.round((0.82 + probability * 0.12) * 1000) / 10,
    timestamp: new Date().toISOString(),
  };
}

const ROUTES: Array<[string, string, string]> = [
  ["DL", "ATL", "JFK"],
  ["UA", "ORD", "SFO"],
  ["AA", "DFW", "LAX"],
  ["BA", "LHR", "JFK"],
  ["EK", "DXB", "BOM"],
  ["AI", "DEL", "LHR"],
  ["SQ", "SIN", "SYD"],
  ["LH", "FRA", "ORD"],
  ["DL", "SEA", "ATL"],
  ["AA", "MIA", "GRU"],
  ["UA", "DEN", "BOS"],
  ["EK", "DXB", "CDG"],
  ["AI", "BOM", "DXB"],
  ["SQ", "SIN", "HND"],
  ["BA", "LHR", "MIA"],
  ["DL", "BOS", "LAX"],
];

export type FlightRow = PredictionResult & { id: string; flightNo: string };

export const FLIGHTS: FlightRow[] = ROUTES.map(([airline, origin, destination], i) => {
  const org = airport(origin);
  const dst = airport(destination);
  const hour = [6, 8, 9, 11, 13, 15, 17, 18, 19, 20, 21, 7, 14, 16, 12, 22][i % 16]!;
  const input: PredictionInput = {
    airline,
    origin,
    destination,
    date: `2026-08-${String(10 + (i % 18)).padStart(2, "0")}`,
    departureTime: `${String(hour).padStart(2, "0")}:${i % 2 ? "35" : "10"}`,
    arrivalTime: `${String((hour + 3) % 24).padStart(2, "0")}:${i % 2 ? "05" : "45"}`,
    distanceKm: haversineKm(org, dst),
    weather: ["clear", "cloudy", "rain", "storm", "fog", "snow"][i % 6]!,
    traffic: 0.35 + ((i * 7) % 60) / 100,
  };
  const result = predictDelay(input);
  return {
    ...result,
    id: `f-${i}`,
    flightNo: `${airline}${(1000 + i * 37) % 9000}`,
  };
});

export const KPIS = {
  flightsAnalyzed: 1_284_902,
  highRisk: FLIGHTS.filter((f) => f.level === "High").length,
  delayRate: 23.7,
  auc: 0.941,
};

export const HOURLY_PATTERN = Array.from({ length: 24 }, (_, h) => ({
  hour: `${String(h).padStart(2, "0")}h`,
  delayRate:
    Math.round((6 + Math.sin(((h - 4) / 24) * Math.PI * 1.15) * 26 + (h > 16 ? 6 : 0)) * 10) / 10,
}));

export const MONTHLY_TREND = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
].map((m, i) => ({
  month: m,
  delayRate: [28.4, 25.1, 21.3, 18.9, 19.8, 26.2, 29.7, 28.1, 19.4, 18.2, 22.6, 30.8][i]!,
  volume: [92, 88, 101, 104, 112, 126, 134, 131, 108, 106, 111, 129][i]!,
}));

export const WEATHER_IMPACT = WEATHER_OPTIONS.map((w) => ({
  weather: w.label,
  delayRate: Math.round((9 + w.weight * 110) * 10) / 10,
}));

export const TRAFFIC_IMPACT = Array.from({ length: 10 }, (_, i) => ({
  traffic: `${(i + 1) * 10}%`,
  delayRate: Math.round((8 + i * 2.9 + (i > 6 ? i * 1.6 : 0)) * 10) / 10,
}));

export const TOP_ROUTES = FLIGHTS.slice(0, 8).map((f) => ({
  route: `${f.input.origin}→${f.input.destination}`,
  delayRate: Math.round(f.probability * 1000) / 10,
}));

export const ROC_CURVE = Array.from({ length: 21 }, (_, i) => {
  const fpr = i / 20;
  return { fpr, tpr: Math.min(1, Math.pow(fpr, 0.28)), baseline: fpr };
});

export const CONFUSION = { tn: 71240, fp: 6120, fn: 5480, tp: 21160 };

export const MODEL_COMPARISON = [
  { model: "Logistic Reg.", auc: 0.842, f1: 0.702 },
  { model: "Random Forest", auc: 0.906, f1: 0.771 },
  { model: "XGBoost", auc: 0.932, f1: 0.803 },
  { model: "LightGBM (prod)", auc: 0.941, f1: 0.818 },
];

export const FEATURE_IMPORTANCE = [
  { feature: "Departure hour", value: 0.221 },
  { feature: "Origin congestion", value: 0.187 },
  { feature: "Weather severity", value: 0.164 },
  { feature: "Route history", value: 0.142 },
  { feature: "Carrier reliability", value: 0.108 },
  { feature: "Seasonality", value: 0.091 },
  { feature: "Stage length", value: 0.087 },
];
