import joblib
import pandas as pd
import numpy as np


# ============================================================
# MODEL
# ============================================================

MODEL_PATH = "models/flight_delay_champion.pkl"


# ============================================================
# FLIGHT INPUT
# ============================================================

DEPARTURE_DELAY = 25.0
TAXI_OUT = 17.0

SCHEDULED_TIME = 135.0
DISTANCE = 750.0

DEP_MIN_OF_DAY = 17 * 60 + 30

MONTH = 11
DAY = 24
DAY_OF_WEEK = 2

AIRLINE = "AA"
ORIGIN_AIRPORT = "ORD"
DESTINATION_AIRPORT = "LGA"

ROUTE = (
    f"{ORIGIN_AIRPORT}_{DESTINATION_AIRPORT}"
)


# ============================================================
# LOAD ARTIFACT
# ============================================================

print("=" * 70)
print("FLITZZ - CHAMPION MODEL TEST")
print("=" * 70)

artifact = joblib.load(
    MODEL_PATH
)

print("\n[OK] PKL loaded")
print(
    "Artifact type:",
    type(artifact)
)


# ============================================================
# GET MODEL
# ============================================================

if isinstance(artifact, dict):

    print("\nArtifact keys:")

    for key in artifact.keys():

        print(
            f"  {key}: "
            f"{type(artifact[key])}"
        )

    if "model" in artifact:

        model = artifact["model"]

    elif "models" in artifact:

        # Only for testing if the artifact
        # contains multiple models.
        model = artifact["models"][0]

        print(
            "\n[WARNING] Using first model "
            "from 'models'."
        )

    else:

        raise RuntimeError(
            "No model found in artifact."
        )

    # --------------------------------------------------------
    # Get training metadata
    # --------------------------------------------------------

    global_mean = artifact.get(
        "global_mean",
        0.0
    )

    lookup_priors = artifact.get(
        "lookup_priors",
        {}
    )

    final_features = artifact.get(
        "final_features",
        None
    )

    cat_targets = artifact.get(
        "cat_targets",
        []
    )

else:

    model = artifact

    global_mean = 0.0

    lookup_priors = {}

    final_features = None

    cat_targets = []


print(
    "\n[OK] Model:"
)

print(
    type(model)
)


# ============================================================
# DISPLAY EXPECTED FEATURES
# ============================================================

if final_features is not None:

    print("\nModel features:")

    for feature in final_features:

        print(
            "  ",
            feature
        )

else:

    print(
        "\n[WARNING] final_features "
        "not found in artifact."
    )


print("\nCategorical features:")

print(cat_targets)


# ============================================================
# BUILD RAW INPUT
# ============================================================

row = {

    "DEPARTURE_DELAY":
        DEPARTURE_DELAY,

    "TAXI_OUT":
        TAXI_OUT,

    "SCHEDULED_TIME":
        SCHEDULED_TIME,

    "DISTANCE":
        DISTANCE,

    "SCHEDULED_SPEED":
        DISTANCE / SCHEDULED_TIME,

    "DEP_MIN_OF_DAY":
        DEP_MIN_OF_DAY,

    "MONTH":
        MONTH,

    "DAY":
        DAY,

    "DAY_OF_WEEK":
        DAY_OF_WEEK,

    "AIRLINE":
        AIRLINE,

    "ORIGIN_AIRPORT":
        ORIGIN_AIRPORT,

    "DESTINATION_AIRPORT":
        DESTINATION_AIRPORT,

    "ROUTE":
        ROUTE,
}


df = pd.DataFrame(
    [row]
)


# ============================================================
# CREATE HISTORICAL PRIOR FEATURES
# ============================================================

print("\nCreating historical priors...")

for column in cat_targets:

    if column not in df.columns:

        raise RuntimeError(
            f"Categorical column "
            f"{column} missing from input."
        )

    value = str(
        df[column].iloc[0]
    )

    prior_map = lookup_priors.get(
        column,
        {}
    )

    historical_value = prior_map.get(
        value,
        global_mean
    )

    historical_column = (
        f"{column}_HIST_DELAY"
    )

    df[
        historical_column
    ] = float(
        historical_value
    )

    print(
        f"{historical_column:<35}: "
        f"{historical_value:.4f}"
    )


# ============================================================
# EXACT FEATURE ORDER
# ============================================================

if final_features is None:

    raise RuntimeError(
        "final_features is missing "
        "from champion artifact."
    )


for feature in final_features:

    if feature not in df.columns:

        df[feature] = 0.0


df = df[
    final_features
].copy()


# ============================================================
# IMPORTANT:
# MATCH LIGHTGBM CATEGORICAL DATA
# ============================================================

for column in cat_targets:

    if column not in df.columns:

        raise RuntimeError(
            f"Categorical feature "
            f"{column} not found."
        )

    # Convert to pandas categorical
    df[column] = (
        df[column]
        .astype(str)
        .astype("category")
    )


# ============================================================
# NUMERIC FEATURES
# ============================================================

for column in df.columns:

    if column in cat_targets:
        continue

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )

    df[column] = (
        df[column]
        .replace(
            [
                np.inf,
                -np.inf
            ],
            np.nan
        )
        .fillna(0.0)
    )


# ============================================================
# SHOW FINAL INPUT
# ============================================================

print()
print("=" * 70)
print("FINAL MODEL INPUT")
print("=" * 70)

print(df)

print()
print("Categorical columns:")
print(
    df.select_dtypes(
        include=["category"]
    ).columns.tolist()
)


# ============================================================
# PREDICTION
# ============================================================

print()
print("=" * 70)
print("RUNNING LIGHTGBM")
print("=" * 70)

try:

    prediction = model.predict(
        df
    )

    predicted_delay = float(
        prediction[0]
    )

    predicted_delay = max(
        0.0,
        predicted_delay
    )

    print()
    print(
        "[SUCCESS] MODEL PREDICTION WORKED!"
    )

    print()
    print(
        "Predicted Arrival Delay:"
    )

    print(
        f"{predicted_delay:.2f} minutes"
    )

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------

    if predicted_delay >= 45:

        risk = "CRITICAL"

    elif predicted_delay >= 30:

        risk = "HIGH"

    elif predicted_delay >= 15:

        risk = "MODERATE"

    else:

        risk = "LOW"

    print(
        f"Risk Level: {risk}"
    )

except Exception as e:

    print()
    print(
        "[ERROR] MODEL PREDICTION FAILED"
    )

    print()
    print(
        str(e)
    )


print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)