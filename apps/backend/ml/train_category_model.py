from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

TRAIN_PATH = DATA_DIR / "train.csv"
VALIDATION_PATH = DATA_DIR / "validation.csv"
MODEL_PATH = MODEL_DIR / "ticket_category_classifier_v1.joblib"

train_df = pd.read_csv(TRAIN_PATH)
validation_df = pd.read_csv(VALIDATION_PATH)

X_train = train_df["text"].astype(str)
y_train = train_df["category"].astype(str)

X_validation = validation_df["text"].astype(str)
y_validation = validation_df["category"].astype(str)

model = Pipeline(
    steps=[
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                min_df=2,
            ),
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=1000,
                random_state=42,
            ),
        ),
    ]
)

model.fit(X_train, y_train)

validation_predictions = model.predict(X_validation)

labels = sorted(y_train.unique())

accuracy = accuracy_score(y_validation, validation_predictions)
report = classification_report(
    y_validation,
    validation_predictions,
    labels=labels,
    zero_division=0,
)
matrix = confusion_matrix(
    y_validation,
    validation_predictions,
    labels=labels,
)

MODEL_DIR.mkdir(exist_ok=True)
joblib.dump(model, MODEL_PATH)

print(f"Training rows: {len(train_df)}")
print(f"Validation rows: {len(validation_df)}")
print(f"Saved model: {MODEL_PATH}")

print(f"\nValidation accuracy: {accuracy:.2%}")

print("\nClassification report:")
print(report)

print("Confusion matrix")
print("Rows = actual category, columns = predicted category")
print("Labels:", labels)
print(matrix)