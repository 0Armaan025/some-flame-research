from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

MANIFEST = (
    ROOT / "data/interim/flex"
    / "20CAL13_timestamped_image_manifest.csv"
)

OUT = ROOT / "data/interim/flex"
OUT.mkdir(parents=True, exist_ok=True)

DATE = "2009-04-10"

# Times transcribed from the 20CAL13 experiment timeline.
events = [
    ("AS Setup Igniters to Ignite", "13:25:00.868", "observed_event"),
    ("AS Setup Completed", "13:25:05.096", "observed_event"),
    ("AS Started", "13:25:47.540", "observed_event"),
    ("AS FCF Diagnostics Delay", "13:26:00.856", "observed_event"),
    ("AS Dispense Start", "13:26:03.866", "observed_event"),
    ("AS Dispense Completed", "13:26:05.162", "observed_event"),
    ("AS Stretch Start", "13:26:10.176", "observed_event"),
    ("AS Stretch Completed", "13:26:10.479", "observed_event"),
    ("AS Needles Retract", "13:26:11.674", "observed_event"),
    ("AS Crew Light", "13:26:11.690", "observed_event"),
    ("AS Burn to Completion / Igniter On",
     "13:26:12.192", "reference_event"),
    ("AS Igniter Off / Retract Start",
     "13:26:13.195", "observed_event"),
    ("AS Retract Completed", "13:26:13.624", "observed_event"),
    ("Programmed 20-second interval endpoint",
     "13:26:32.192", "programmed_endpoint_not_observed"),
    ("AS Completed", "13:26:55.324", "observed_event"),
]

event_df = pd.DataFrame(
    events,
    columns=["event", "time", "event_type"]
)

event_df["timestamp"] = pd.to_datetime(
    DATE + " " + event_df["time"],
    errors="raise"
)

ignition_time = event_df.loc[
    event_df["event_type"] == "reference_event",
    "timestamp"
].iloc[0]

event_df["elapsed_from_ignition_s"] = (
    event_df["timestamp"] - ignition_time
).dt.total_seconds()

event_path = OUT / "20CAL13_event_timeline.csv"
event_df.to_csv(event_path, index=False)

# Load every indexed frame, including unavailable images.
frames = pd.read_csv(MANIFEST)

frames["camera_timestamp"] = pd.to_datetime(
    frames["camera_timestamp"],
    errors="raise"
)

frames["elapsed_from_ignition_s"] = (
    frames["camera_timestamp"] - ignition_time
).dt.total_seconds()

frames["timing_reference"] = (
    "experiment_timeline_igniter_on"
)

frame_path = OUT / "20CAL13_ignition_aligned_frames.csv"
frames.to_csv(frame_path, index=False)

# Find the nearest indexed frame to each event in each segment.
nearest_rows = []

for segment, group in frames.groupby("segment"):
    group = group.sort_values("camera_timestamp")

    for _, event in event_df.iterrows():
        differences = (
            group["camera_timestamp"] - event["timestamp"]
        ).dt.total_seconds()

        nearest_index = differences.abs().idxmin()
        nearest = group.loc[nearest_index]

        nearest_rows.append({
            "segment": segment,
            "event": event["event"],
            "event_type": event["event_type"],
            "event_timestamp": event["timestamp"],
            "nearest_img_num": nearest["ImgNum"],
            "nearest_frame_timestamp": nearest["camera_timestamp"],
            "frame_minus_event_s": differences.loc[nearest_index],
            "image_available": nearest["image_available"],
            "image_status": nearest["image_status"],
        })

nearest_df = pd.DataFrame(nearest_rows)

nearest_path = OUT / "20CAL13_event_nearest_frames.csv"
nearest_df.to_csv(nearest_path, index=False)

print("\nEVENT TIMELINE")
print(
    event_df[
        ["event", "elapsed_from_ignition_s", "event_type"]
    ].to_string(index=False)
)

print("\nCAMERA COVERAGE RELATIVE TO IGNITION")

for segment, group in frames.groupby("segment"):
    print(f"\nSegment {segment}")
    print("First frame relative time:",
          round(group["elapsed_from_ignition_s"].min(), 3))
    print("Last frame relative time:",
          round(group["elapsed_from_ignition_s"].max(), 3))
    print("Indexed frames:", len(group))
    print("Available images:",
          int(group["image_available"].sum()))

print("\nNEAREST FRAMES TO EVENTS")
print(
    nearest_df[
        [
            "segment",
            "event",
            "nearest_img_num",
            "frame_minus_event_s",
            "image_available",
        ]
    ].to_string(index=False)
)

print("\nSAVED:")
print(event_path)
print(frame_path)
print(nearest_path)
