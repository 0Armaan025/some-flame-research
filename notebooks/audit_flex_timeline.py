from pathlib import Path
from zipfile import ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "flex" / "part-01"

FILES = {
    "chamber": (
        "20CAL13_Chamber_Readings.txt",
        "FCU TimeStamp",
    ),
    "testpoint": (
        "20CAL13_Testpoint_Settings.txt",
        "PIP TimeStamp",
    ),
    "radiometer": (
        "20CAL13_Radiometer_Readings.txt",
        "PIP TimeStamp",
    ),
}

def audit_stream(name, filename, timestamp_column):
    path = DATA / filename

    print(f"\n{'=' * 65}")
    print(f"{name.upper()} — {filename}")
    print("=" * 65)

    df = pd.read_csv(path, encoding="latin-1")

    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("Timestamp column exists:", timestamp_column in df.columns)

    if timestamp_column not in df.columns:
        print("Available timestamp-like columns:")
        print([c for c in df.columns if "time" in c.lower()])
        return

    timestamps = pd.to_datetime(
        df[timestamp_column],
        errors="coerce"
    ).dropna().sort_values()

    if timestamps.empty:
        print("No valid timestamps.")
        return

    intervals = timestamps.diff().dt.total_seconds().dropna()

    print("First timestamp:", timestamps.iloc[0])
    print("Last timestamp: ", timestamps.iloc[-1])
    print("Valid timestamps:", len(timestamps))

    if not intervals.empty:
        print("Median interval (s):", intervals.median())
        print("Minimum interval (s):", intervals.min())
        print("Maximum interval (s):", intervals.max())
        print("Intervals greater than 2 seconds:",
              int((intervals > 2).sum()))

    print("\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))

    print("\nLast 3 rows:")
    print(df.tail(3).to_string(index=False))


for name, (filename, timestamp_column) in FILES.items():
    audit_stream(name, filename, timestamp_column)


# Camera image-index metadata
for segment in ["A", "B", "D"]:
    path = DATA / f"20CAL13{segment}.txt"

    if not path.exists():
        print(f"\nMissing image-index file: {path.name}")
        continue

    print(f"\n{'=' * 65}")
    print(f"IMAGE INDEX — {path.name}")
    print("=" * 65)

    # First two lines are metadata; actual CSV header is line 3.
    with open(path, encoding="latin-1") as f:
        meta_line1 = f.readline().strip()
        meta_line2 = f.readline().strip()
    print("Metadata:", meta_line1)
    print("Metadata:", meta_line2)

    df = pd.read_csv(path, skiprows=2, encoding="latin-1")

    print("Rows:", len(df))
    print("Columns:", list(df.columns))
    print("\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))
    print("\nLast 3 rows:")
    print(df.tail(3).to_string(index=False))


# Inspect archive size without extracting it
archive = DATA / "20CAL13D.zip"

if archive.exists():
    print(f"\n{'=' * 65}")
    print("IMAGE ARCHIVE")
    print("=" * 65)

    with ZipFile(archive) as z:
        members = z.infolist()
        images = [
            item for item in members
            if item.filename.lower().endswith(
                (".bmp", ".png", ".jpg", ".jpeg", ".fci")
            )
        ]

        print("Total archive entries:", len(members))
        print("Image/FCI entries:", len(images))
        print("Uncompressed image/FCI size (GB):",
              round(sum(x.file_size for x in images) / 1e9, 3))

        print("Example entries:")
        for item in images[:10]:
            print(item.filename, item.file_size)
