from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "data" / "support_tickets_10000_synthetic.csv"

EXPECTED_COLUMNS = {"ticket_id", "text", "category"}
EXPECTED_CATEGORIES = {
    "ACCOUNT_ACCESS",
    "BILLING_PAYMENT",
    "TECHNICAL_ISSUE",
    "FEATURE_REQUEST",
    "HOW_TO_SUPPORT",
    "OTHER",
}

df = pd.read_csv(DATASET_PATH)

print("Dataset path:", DATASET_PATH)
print("\nShape (rows, columns):", df.shape)
print("\nColumns:", df.columns.tolist())

missing_columns = EXPECTED_COLUMNS - set(df.columns)
if missing_columns:
    raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

print("\nMissing values per column:")
print(df[["ticket_id", "text", "category"]].isna().sum())

df["text"] = df["text"].fillna("").astype(str).str.strip()
df["category"] = df["category"].fillna("").astype(str).str.strip()

print("\nEmpty text rows:", (df["text"] == "").sum())
print("Empty category rows:", (df["category"] == "").sum())

print("\nCategory counts:")
print(df["category"].value_counts().sort_index())

unexpected_categories = set(df["category"]) - EXPECTED_CATEGORIES
print("\nUnexpected categories:", sorted(unexpected_categories))

exact_duplicate_rows = df.duplicated().sum()
duplicate_text_rows = df.duplicated(subset=["text"]).sum()

print("\nExact duplicate rows:", exact_duplicate_rows)
print("Duplicate text rows:", duplicate_text_rows)

duplicate_examples = (
    df[df.duplicated(subset=["text"], keep=False)]
    .sort_values("text")[["ticket_id", "text", "category"]]
    .head(20)
)

print("\nFirst duplicate-text examples:")
print(duplicate_examples.to_string(index=False))