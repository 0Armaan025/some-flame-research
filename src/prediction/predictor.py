import re
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

CSV_PATH = "../../data/raw/flex/PSI-69_Experimental table_FLEX.csv"

FUEL_OPTS = ["Methanol", "Heptane"]
MONTH_OPTS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
YEAR_OPTS = ["2009", "2010", "2011"]
TOD_OPTS = ["Morning", "Afternoon", "Evening", "Night"]


def parse_year(date_str):
    """Normalize mixed 2-digit / 4-digit year formats to 4-digit."""
    s = str(date_str).strip()
    parts = s.split("/")
    if len(parts) < 3:
        return None
    yr = parts[-1]
    if len(yr) == 2:
        return "20" + yr
    return yr if yr.isdigit() else None


def parse_month(date_str):
    s = str(date_str).strip()
    parts = s.split("/")
    if len(parts) < 2:
        return None
    try:
        m = int(parts[0])
        if 1 <= m <= 12:
            return MONTH_OPTS[m - 1]
    except ValueError:
        pass
    return None


def time_bucket(gmt_str):
    try:
        h = int(str(gmt_str).strip().split(":")[0])
    except (ValueError, AttributeError, IndexError):
        return "Unknown"
    if 5 <= h < 12:
        return "Morning"
    if 12 <= h < 17:
        return "Afternoon"
    if 17 <= h < 21:
        return "Evening"
    return "Night"


def load_and_prepare():
    df = pd.read_csv(CSV_PATH, encoding="latin-1")
    df = df[["Fuel", "Test Date", "Test GMT", "Test end"]].copy()
    df = df.dropna(subset=["Fuel", "Test end"])

    df["Fuel"] = df["Fuel"].astype(str).str.strip()
    df["Test end"] = df["Test end"].astype(str).str.strip()

    df["Year"] = df["Test Date"].apply(parse_year)
    df["Month"] = df["Test Date"].apply(parse_month)
    df["Time of Day"] = df["Test GMT"].apply(time_bucket)

    df = df.dropna(subset=["Year", "Month", "Time of Day"])

    feature_cols = ["Fuel", "Month", "Year", "Time of Day"]
    X = df[feature_cols].copy()
    y = df["Test end"].copy()
    return X, y, feature_cols


def train_model(X, y, feature_cols):
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), feature_cols),
        ]
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", LogisticRegression(max_iter=3000)),
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    return model, acc


def prompt_choice(prompt, options):
    print(f"  Options: {', '.join(options)}")
    while True:
        val = input(f"  {prompt}: ").strip()
        # case-insensitive match
        for opt in options:
            if val.lower() == opt.lower():
                return opt
        print(f"    Invalid. Pick one of: {', '.join(options)}")


def ask_questions():
    print("\n" + "=" * 55)
    print(" FLAME TEST OUTCOME PREDICTOR")
    print("=" * 55)
    print("Answer the following general questions.")
    print("Do NOT enter numerical values.\n")

    fuel = prompt_choice("Fuel type", FUEL_OPTS)
    month = prompt_choice("Test month", MONTH_OPTS)
    year = prompt_choice("Test year", YEAR_OPTS)
    tod = prompt_choice("Time of day", TOD_OPTS)

    return pd.DataFrame([{
        "Fuel": fuel,
        "Month": month,
        "Year": year,
        "Time of Day": tod,
    }])


def main():
    X, y, feature_cols = load_and_prepare()
    model, acc = train_model(X, y, feature_cols)

    print(f"\nTrained on {len(X)} records using categorical features only.")
    print(f"Features: {', '.join(feature_cols)}")
    print(f"Target classes: {sorted(y.unique())}")
    print(f"Model accuracy (held-out test split): {acc:.2%}")

    user_input = ask_questions()

    pred_class = model.predict(user_input)[0]
    probs = model.predict_proba(user_input)[0]
    classes = model.classes_
    prob_dict = {cls: round(float(p) * 100, 1) for cls, p in zip(classes, probs)}

    print("\n" + "-" * 55)
    print("Inputs:")
    for col in feature_cols:
        print(f"  - {col}: {user_input.iloc[0][col]}")
    print(f"Predicted test end: {pred_class}")
    print("Prediction confidence:")
    for label in sorted(prob_dict, key=prob_dict.get, reverse=True):
        print(f"  - {label}: {prob_dict[label]}%")
    print("-" * 55)


if __name__ == "__main__":
    main()
