from pathlib import Path
from zipfile import ZipFile
from collections import Counter
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "flex" / "part-01"

for segment in ["A", "B", "D"]:
    print(f"\n{'=' * 65}")
    print(f"SEGMENT {segment}")
    print("=" * 65)

    index_path = DATA / f"20CAL13{segment}.txt"
    zip_path = DATA / f"20CAL13{segment}.zip"

    if index_path.exists():
        df = pd.read_csv(
            index_path,
            encoding="latin-1",
            skiprows=2,
            skipinitialspace=True
        )

        print("\nINDEX")
        print("Rows:", len(df))
        print("Columns:", list(df.columns))

        for column in ["FileName", "FileNum", "FileIndex",
                       "ImgNum", "DiskNum", "Mseconds",
                       "Delta", "Date", "MTimeStamp"]:
            if column in df.columns:
                print(f"\n{column}:")
                print(df[column].head(8).to_string(index=False))

    else:
        print("Index file missing.")

    if not zip_path.exists():
        print("\nZIP missing.")
        continue

    with ZipFile(zip_path) as archive:
        members = [
            item for item in archive.infolist()
            if not item.is_dir()
        ]

        extensions = Counter(
            Path(item.filename).suffix.lower() or "[no extension]"
            for item in members
        )

        print("\nARCHIVE")
        print("Entries:", len(members))
        print("Extension counts:", dict(extensions))
        print("Uncompressed size (GB):",
              round(sum(x.file_size for x in members) / 1e9, 3))

        print("\nFirst 20 archive entries:")
        for item in members[:20]:
            print(item.filename, item.file_size)

        print("\nLast 5 archive entries:")
        for item in members[-5:]:
            print(item.filename, item.file_size)
