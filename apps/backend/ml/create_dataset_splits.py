from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SOURCE_PATH = DATA_DIR / "support_tickets_10000_synthetic.csv"
TRAIN_PATH = DATA_DIR / "train.csv"
VALIDATION_PATH = DATA_DIR / "validation.csv"
TEST_PATH = DATA_DIR / "test.csv"

RANDOM_STATE = 42

df = pd.read_csv(SOURCE_PATH)

train_df, remaining_df = train_test_split(
    df,
    test_size=0.30,
    random_state=RANDOM_STATE,
    stratify=df["category"],
)

validation_df, test_df = train_test_split(
    remaining_df,
    test_size=0.50,
    random_state=RANDOM_STATE,
    stratify=remaining_df["category"],
)

train_df.to_csv(TRAIN_PATH, index=False)
validation_df.to_csv(VALIDATION_PATH, index=False)
test_df.to_csv(TEST_PATH, index=False)

for split_name, split_df in {
    "Train": train_df,
    "Validation": validation_df,
    "Test": test_df,
}.items():
    print(f"\n{split_name}: {len(split_df)} rows")
    print(split_df["category"].value_counts().sort_index())