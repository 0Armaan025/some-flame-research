import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_PATH = os.path.join(ROOT, "data", "raw", "flex", "PSI-69_Experimental table_FLEX.csv")

df = pd.read_csv(CSV_PATH, encoding="latin-1")

print("\n=== SHAPE ===")
print(df.shape)

print("\n=== COLUMNS ===")
print(df.dtypes)

print("\n=== OUTCOME DISTRIBUTION ===")
print(df["Test end"].value_counts(dropna=False))

print("\n=== FUEL DISTRIBUTION ===")
print(df["Fuel"].value_counts(dropna=False))

print("\n=== MISSING VALUES ===")
print(df.isna().sum())

print("\n=== NUMERIC SUMMARY ===")
print(df.describe(include="all").T)

print("\n=== OUTCOME BY FUEL ===")
print(pd.crosstab(df["Fuel"], df["Test end"]))

print("\n=== EXPERIMENTAL PRESSURE RANGE ===")
print(df["Ambient pressure; mmHg"].describe())
