from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "flex" / "part-01"

def load_csv(name, skiprows=0):
    return pd.read_csv(
        DATA / name,
        encoding="latin-1", skipinitialspace=True,
        skiprows=skiprows
    )

def report_clock(df, label, pip_col, main_col, ms_col):
    print(f"\n--- {label} ---")

    required = [pip_col, main_col, ms_col]
    if not all(c in df.columns for c in required):
        print("Required clock columns unavailable.")
        print("Available:", [c for c in df.columns if "time" in c.lower()])
        return

    pip = pd.to_datetime(df[pip_col], errors="coerce")

    main = pd.to_datetime(
        df[main_col],
        errors="coerce"
    ) + pd.to_timedelta(
        pd.to_numeric(df[ms_col], errors="coerce"),
        unit="ms"
    )

    offset = (pip - main).dt.total_seconds().dropna()

    if offset.empty:
        print("No valid paired timestamps.")
        return

    print("Valid pairs:", len(offset))
    print("Median PIP - main (s):", offset.median())
    print("Minimum offset (s):", offset.min())
    print("Maximum offset (s):", offset.max())
    print("First 5 offsets:")
    print(offset.head().to_string(index=False))


testpoint = load_csv("20CAL13_Testpoint_Settings.txt")
radiometer = load_csv("20CAL13_Radiometer_Readings.txt")

report_clock(
    testpoint,
    "TESTPOINT",
    "PIP TimeStamp",
    "MAIN_COMPUTER_TIME(GMT)",
    "MAIN_COMPUTER_MILLISECONDS(N/A)"
)

report_clock(
    radiometer,
    "RADIOMETER",
    "PIP TimeStamp",
    "MAIN_COMPUTER_TIME(GMT)",
    "MAIN_COMPUTER_MILLISECONDS(N/A)"
)

# Radiometer's own frame clock versus main computer clock
print("\n--- RADIOMETER FRAME CLOCK ---")

frame_col = "RADIOMETER_100HZ_FRAME_TIME(GMT)"
frame_ms_col = "RADIOMETER_100HZ_FRAME_MILLISECONDS(N/A)"
main_col = "MAIN_COMPUTER_TIME(GMT)"
main_ms_col = "MAIN_COMPUTER_MILLISECONDS(N/A)"

if all(c in radiometer.columns for c in [
    frame_col, frame_ms_col, main_col, main_ms_col
]):
    frame = pd.to_datetime(radiometer[frame_col], errors="coerce")
    frame += pd.to_timedelta(
        pd.to_numeric(radiometer[frame_ms_col], errors="coerce"),
        unit="ms"
    )

    main = pd.to_datetime(radiometer[main_col], errors="coerce")
    main += pd.to_timedelta(
        pd.to_numeric(radiometer[main_ms_col], errors="coerce"),
        unit="ms"
    )

    offsets = (frame - main).dt.total_seconds().dropna()

    print("Valid pairs:", len(offsets))
    if not offsets.empty:
        print("Median frame - main (s):", offsets.median())
        print("Minimum (s):", offsets.min())
        print("Maximum (s):", offsets.max())

# Inspect image-index timestamp fields
for segment in ["A", "B", "D"]:
    path = DATA / f"20CAL13{segment}.txt"

    if not path.exists():
        continue

    df = pd.read_csv(
        path,
        encoding="latin-1", skipinitialspace=True,
        skiprows=2
    )

    print(f"\n--- IMAGE INDEX {segment} ---")
    print("Columns:", list(df.columns))

    useful = [
        c for c in [
            "ImgNum", "Mseconds", "Delta",
            "Date", "MTimeStamp", "FileName"
        ]
        if c in df.columns
    ]

    print(df[useful].head(5).to_string(index=False))
    print(df[useful].tail(5).to_string(index=False))
