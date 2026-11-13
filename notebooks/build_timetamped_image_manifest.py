from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INDEX_DIR = ROOT / "data" / "raw" / "flex" / "part-01"
MANIFEST_PATH = (
    ROOT / "data" / "interim" / "flex"
    / "20CAL13_image_manifest.csv"
)

OUTPUT_PATH = (
    ROOT / "data" / "interim" / "flex"
    / "20CAL13_timestamped_image_manifest.csv"
)

manifest = pd.read_csv(MANIFEST_PATH)

segments = []

for segment in ["A", "B", "D"]:
    print(f"Processing segment {segment}...")

    index_path = INDEX_DIR / f"20CAL13{segment}.txt"

    index = pd.read_csv(
        index_path,
        encoding="latin-1",
        skiprows=2,
        skipinitialspace=True
    )

    index["ImgNum"] = pd.to_numeric(
        index["ImgNum"], errors="raise"
    ).astype("int64")

    # Preserve the original timing fields.
    index["Date"] = index["Date"].astype(str).str.strip()
    index["MTimeStamp"] = (
        index["MTimeStamp"].astype(str).str.strip()
    )

    # Candidate absolute timestamp, without assuming timezone.
    index["camera_timestamp"] = pd.to_datetime(
        index["Date"] + " " + index["MTimeStamp"],
        errors="coerce"
    )

    if index["camera_timestamp"].isna().any():
        bad = index.loc[
            index["camera_timestamp"].isna(),
            ["ImgNum", "Date", "MTimeStamp"]
        ]

        raise ValueError(
            f"Unparseable timestamps in {segment}:\n{bad.head(10)}"
        )

    index = index.sort_values("ImgNum").reset_index(drop=True)

    index["segment"] = segment

    # Calculate intervals using recorded timestamps.
    index["frame_interval_s"] = (
        index["camera_timestamp"].diff().dt.total_seconds()
    )

    # Relative time within each camera segment.
    index["elapsed_from_segment_start_s"] = (
        index["camera_timestamp"]
        - index["camera_timestamp"].iloc[0]
    ).dt.total_seconds()

    segments.append(index)

timing = pd.concat(segments, ignore_index=True)

# Join the timing data to the existing image availability manifest.
result = manifest.merge(
    timing,
    on=["segment", "ImgNum"],
    how="left",
    validate="one_to_one",
    suffixes=("_manifest", "")
)

if len(result) != len(manifest):
    raise ValueError("Manifest row count changed during merge.")

if result["camera_timestamp"].isna().any():
    raise ValueError("Some indexed frames have no timestamp.")

result = result.sort_values(
    ["segment", "ImgNum"]
).reset_index(drop=True)

# Explicitly document what this timestamp represents.
result["timestamp_status"] = (
    "camera_index_timestamp_timezone_unverified"
)

result.to_csv(OUTPUT_PATH, index=False)

print("\nTIMESTAMPED MANIFEST")
print("Rows:", len(result))
print("Available images:", result["image_available"].sum())
print("Unavailable images:", (~result["image_available"]).sum())

print("\nTIME RANGES")
for segment, group in result.groupby("segment"):
    print(
        segment,
        group["camera_timestamp"].min(),
        "to",
        group["camera_timestamp"].max()
    )

print("\nFRAME INTERVAL SUMMARY")
for segment, group in result.groupby("segment"):
    print(f"\n{segment}")
    print(
        group["frame_interval_s"].describe(
            percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]
        )
    )

print("\nSaved:", OUTPUT_PATH)
