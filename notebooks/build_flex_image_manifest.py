from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "flex" / "part-01"
OUTPUT = ROOT / "data" / "interim" / "flex"

OUTPUT.mkdir(parents=True, exist_ok=True)


def get_image_number(filename):
    match = re.search(r"(\d+)$", Path(filename).stem)
    return int(match.group(1)) if match else None


all_manifests = []

for segment in ["A", "B", "D"]:
    print(f"\n{'=' * 60}")
    print(f"PROCESSING SEGMENT {segment}")
    print("=" * 60)

    index_path = DATA / f"20CAL13{segment}.txt"
    archive_path = DATA / f"20CAL13{segment}.zip"

    df = pd.read_csv(
        index_path,
        encoding="latin-1",
        skiprows=2,
        skipinitialspace=True
    )

    if "ImgNum" not in df.columns:
        raise ValueError(f"{segment}: ImgNum column missing")

    df["ImgNum"] = pd.to_numeric(
        df["ImgNum"], errors="raise"
    ).astype("int64")

    if df["ImgNum"].duplicated().any():
        duplicates = df.loc[
            df["ImgNum"].duplicated(keep=False), "ImgNum"
        ].tolist()
        raise ValueError(
            f"{segment}: duplicate index ImgNum values: {duplicates[:20]}"
        )

    archive_map = {}
    image_format = None

    if archive_path.exists():
        with ZipFile(archive_path) as archive:
            members = [
                name for name in archive.namelist()
                if name.lower().endswith(
                    (".bmp", ".tif", ".tiff", ".png", ".jpg")
                )
            ]

        suffixes = [get_image_number(name) for name in members]

        if None in suffixes:
            raise ValueError(
                f"{segment}: archive contains filenames "
                "without numeric suffixes"
            )

        duplicates = [
            number
            for number, count in Counter(suffixes).items()
            if count > 1
        ]

        if duplicates:
            raise ValueError(
                f"{segment}: duplicate archive image numbers: "
                f"{duplicates[:20]}"
            )

        archive_map = dict(zip(suffixes, members))

        formats = {
            Path(name).suffix.lower()
            for name in members
        }

        image_format = ",".join(sorted(formats))

    df["archive_member"] = df["ImgNum"].map(archive_map)

    df["image_available"] = df["archive_member"].notna()

    df["segment"] = segment
    df["image_format"] = image_format

    df["archive_path"] = (
        str(archive_path.relative_to(ROOT))
        if archive_path.exists()
        else None
    )

    df["image_status"] = df["image_available"].map({
        True: "available_in_archive",
        False: (
            "archive_missing"
            if not archive_path.exists()
            else "image_not_in_archive"
        )
    })

    available = int(df["image_available"].sum())
    missing = len(df) - available

    print("Indexed frames:", len(df))
    print("Available images:", available)
    print("Unavailable images:", missing)

    if archive_path.exists():
        unmatched_archive = (
            set(archive_map) - set(df["ImgNum"])
        )
        print("Archive images without index rows:",
              len(unmatched_archive))

    all_manifests.append(df)

manifest = pd.concat(
    all_manifests,
    ignore_index=True
)

output_path = OUTPUT / "20CAL13_image_manifest.csv"

manifest.to_csv(output_path, index=False)

print("\n" + "=" * 60)
print("FINAL MANIFEST")
print("=" * 60)

print(manifest.groupby(
    ["segment", "image_status"]
).size().to_string())

print("\nSaved:", output_path)
print("Total indexed frames:", len(manifest))
