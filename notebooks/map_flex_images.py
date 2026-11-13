from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "flex" / "part-01"

FIELDS = [
    "ImgNum",
    "DiskNum",
    "FileNum",
    "FileIndex",
    "Mseconds",
    "Delta",
    "Date",
    "MTimeStamp",
    "FileName",
]

def numeric_suffix(filename):
    match = re.search(r"(\d+)$", Path(filename).stem)
    return int(match.group(1)) if match else None

for segment in ["A", "B", "D"]:
    print(f"\n{'=' * 70}")
    print(f"SEGMENT {segment}")
    print("=" * 70)

    index_path = DATA / f"20CAL13{segment}.txt"
    archive_path = DATA / f"20CAL13{segment}.zip"

    if not index_path.exists():
        print("Index missing.")
        continue

    df = pd.read_csv(
        index_path,
        encoding="latin-1",
        skiprows=2,
        skipinitialspace=True
    )

    print("\nINDEX FIELD SUMMARY")

    for field in FIELDS:
        if field not in df.columns:
            continue

        values = df[field].dropna()

        print(f"\n{field}")
        print("Non-null:", len(values))
        print("Unique:", values.nunique())
        print("First 8:", values.head(8).tolist())
        print("Last 8:", values.tail(8).tolist())

    if not archive_path.exists():
        print("\nNo ZIP archive.")
        continue

    with ZipFile(archive_path) as z:
        images = [
            Path(name).name
            for name in z.namelist()
            if name.lower().endswith(
                (".bmp", ".tif", ".tiff", ".png", ".jpg")
            )
        ]

    print("\nARCHIVE IMAGE SUMMARY")
    print("Image count:", len(images))
    print("First 10:", images[:10])
    print("Last 10:", images[-10:])

    numbers = [
        numeric_suffix(name)
        for name in images
    ]
    numbers = [n for n in numbers if n is not None]

    print("Numeric suffix count:", len(numbers))
    print("Unique numeric suffixes:", len(set(numbers)))

    duplicates = [
        n for n, count in Counter(numbers).items()
        if count > 1
    ]

    print("Duplicate numeric suffixes:", duplicates[:20])

    # Test whether image suffixes match any index fields.
    print("\nINDEX NUMERIC FIELD COMPARISON")

    for field in ["ImgNum", "FileNum", "FileIndex"]:
        if field not in df.columns:
            continue

        index_values = pd.to_numeric(
            df[field], errors="coerce"
        ).dropna()

        archive_values = set(numbers)
        matches = sum(
            int(value) in archive_values
            for value in index_values
        )

        print(
            field,
            "index values:", len(index_values),
            "matching numeric values:", matches
        )

    print("\nFIRST 15 INDEX ROWS")
    available = [f for f in FIELDS if f in df.columns]
    print(df[available].head(15).to_string(index=False))

# Check whether A payload exists elsewhere in the local dataset.
print("\n" + "=" * 70)
print("SEARCHING FOR SEGMENT A PAYLOAD")
print("=" * 70)

for path in ROOT.rglob("*"):
    if path.is_file() and "20CAL13A" in path.name:
        print(path.relative_to(ROOT), path.stat().st_size)
