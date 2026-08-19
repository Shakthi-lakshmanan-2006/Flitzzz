from pathlib import Path
import pandas as pd


# Project root = folder containing test_flights.py
PROJECT_ROOT = Path(__file__).resolve().parent

# Dataset location
INPUT_FILE = (
    PROJECT_ROOT
    / "backend"
    / "ml"
    / "datasets"
    / "flights.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "backend"
    / "ml"
    / "artifacts"
    / "real_test_flights.csv"
)


print("=" * 70)
print("FLITZZ - REAL FLIGHT TEST DATA")
print("=" * 70)

print(f"\nDataset:")
print(INPUT_FILE)


if not INPUT_FILE.exists():

    print("\n[ERROR] Dataset not found!")
    print(f"Expected location:\n{INPUT_FILE}")

    print("\nAvailable files in datasets:")

    dataset_dir = (
        PROJECT_ROOT
        / "backend"
        / "ml"
        / "datasets"
    )

    if dataset_dir.exists():

        for file in dataset_dir.iterdir():
            print("  ", file.name)

    else:

        print(
            f"Dataset directory does not exist:\n"
            f"{dataset_dir}"
        )

    raise SystemExit(1)


print("\n[OK] Dataset found")


df = pd.read_csv(INPUT_FILE)

print(
    f"[OK] Loaded {len(df):,} rows"
)

print(
    f"[OK] Columns: {len(df.columns)}"
)