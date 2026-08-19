import type { PredictionResult } from "./flitz-data";

const KEY = "flitz-last-prediction";

export function savePrediction(result: PredictionResult) {
  try {
    localStorage.setItem(KEY, JSON.stringify(result));
  } catch {
    /* ignore */
  }
}

export function loadPrediction(): PredictionResult | null {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as PredictionResult) : null;
  } catch {
    return null;
  }
}
