from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "flex" / "part-01"

FIELDS = [
    "ImgNum",
    "Date",
    "MTimeStamp",
    "Mseconds",
    "Delta",
    "FileName",
]


def describe_intervals(values, label):
    values = pd.to_datetime(values, errors="coerce").dropna()

    if len(values) < 2:
        print(f"{label}: insufficient parseable timestamps")
        return

    intervals = values.diff().dt.total_seconds().dropna()

    print(f"\n{label}")
    print("Parsed timestamps:", len(values))
    print("First:", values.iloc[0])
    print("Last:", values.iloc[-1])
    print("Duplicate timestamps:", values.duplicated().sum())
    print("Negative intervals:", (intervals < 0).sum())
    print("Zero intervals:", (intervals == 0).sum())
    print("Interval seconds:")
    print(intervals.describe(
        percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]
    ).to_string())


for segment in ["A", "B", "D"]:
    print("\n" + "=" * 75)
    print("SEGMENT", segment)
    print("=" * 75)

    path = DATA / f"20CAL13{segment}.txt"

    df = pd.read_csv(
        path,
        encoding="latin-1",
        skiprows=2,
        skipinitialspace=True
    )

    available_fields = [
        field for field in FIELDS
        if field in df.columns
    ]

    print("\nRAW SAMPLE")
    print(df[available_fields].head(12).to_string(index=False))

    print("\nFIELD TYPES")
    print(df[available_fields].dtypes.to_string())

    print("\nMISSING VALUES")
    print(df[available_fields].isna().sum().to_string())

    df = df.sort_values("ImgNum").reset_index(drop=True)

    print("\nIMGNUM")
    print("Minimum:", df["ImgNum"].min())
    print("Maximum:", df["ImgNum"].max())
    print("Unique:", df["ImgNum"].nunique())
    print("Monotonic:", df["ImgNum"].is_monotonic_increasing)

    # Examine MTimeStamp without assuming its format.
    if "MTimeStamp" in df.columns:
        parsed = pd.to_datetime(
            df["MTimeStamp"],
            errors="coerce"
        )

        print("\nMTIMESTAMP PARSING")
        print("Successfully parsed:", parsed.notna().sum())
        print("Failed:", parsed.isna().sum())

        if parsed.notna().any():
            describe_intervals(
                parsed,
                "MTimeStamp ordered by ImgNum"
            )

    # Examine Date + MTimeStamp as a separate candidate.
    if "Date" in df.columns and "MTimeStamp" in df.columns:
        combined = (
            df["Date"].astype(str).str.strip()
            + " "
            + df["MTimeStamp"].astype(str).str.strip()
        )

        parsed_combined = pd.to_datetime(
            combined,
            errors="coerce"
        )

        print("\nDATE + MTIMESTAMP PARSING")
        print("Successfully parsed:", parsed_combined.notna().sum())
        print("Failed:", parsed_combined.isna().sum())

        if parsed_combined.notna().any():
            describe_intervals(
                parsed_combined,
                "Date + MTimeStamp ordered by ImgNum"
            )

    # Numeric summaries; interpretation still requires documentation.
    for field in ["Mseconds", "Delta"]:
        if field not in df.columns:
            continue

        numeric = pd.to_numeric(
            df[field], errors="coerce"
        )

        print(f"\n{field} NUMERIC SUMMARY")
        print(numeric.describe().to_string())

        print("First 12:", numeric.head(12).tolist())
        print("Last 12:", numeric.tail(12).tolist())

    # Preserve all raw timing fields in a separate audit file.
    output = ROOT / "data" / "interim" / "flex"
    output.mkdir(parents=True, exist_ok=True)

    df[available_fields].to_csv(
        output / f"20CAL13{segment}_frame_timing_raw.csv",
        index=False
    )

print("\nTiming audit completed.")
