import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
path = os.path.join(ROOT, "data", "raw", "flex", "PSI-69_Experimental table_FLEX.csv")
df = pd.read_csv(path, encoding="latin-1")

print("Duplicate experiment identifiers:")
print(df[df["FLEX Identifier"].duplicated(keep=False)]
      [["FLEX Identifier", "Fuel", "Test end"]].to_string(index=False))

print("\nZero-pressure experiments:")
print(df[df["Ambient pressure; mmHg"] == 0]
      [["FLEX Identifier", "Fuel", "Test end"]].to_string(index=False))

print("\nOutcome counts by pressure range:")
df["pressure_group"] = pd.cut(
    df["Ambient pressure; mmHg"],
    bins=[-1, 100, 500, 1000, 3000],
    labels=["0-100", "100-500", "500-1000", "1000-3000"]
)
print(pd.crosstab(df["pressure_group"], df["Test end"]))

print("\nMissingness by outcome:")
print(df.groupby("Test end").apply(
    lambda x: x.isna().sum(),
    include_groups=False
))
