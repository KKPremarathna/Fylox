from pathlib import Path
from typing import TypedDict

import joblib


class CategorySuggestion(TypedDict):
    suggested_category: str
    confidence: float


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "ticket_category_classifier_v1.joblib"

_model = None


def get_category_model():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Category model was not found at: {MODEL_PATH}"
            )

        _model = joblib.load(MODEL_PATH)

    return _model


def suggest_ticket_category(
    subject: str,
    description: str,
) -> CategorySuggestion:
    text = f"{subject}\n\n{description}".strip()

    if not text:
        raise ValueError("Ticket text cannot be empty.")

    model = get_category_model()

    probabilities = model.predict_proba([text])[0]
    best_index = probabilities.argmax()

    return {
        "suggested_category": str(model.classes_[best_index]),
        "confidence": float(probabilities[best_index]),
    }