from pathlib import Path

import joblib


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "ticket_category_classifier_v1.joblib"

model = joblib.load(MODEL_PATH)

challenge_tickets = [
    "I paid already, but the premium features are still unavailable.",
    "The site keeps spinning forever whenever I try to open reports.",
    "Can our organization use a different color scheme?",
    "I need guidance on removing an old team member.",
    "I have an enquiry regarding a business partnership.",
    "I was locked out because my two-step verification device was replaced.",
]

probabilities = model.predict_proba(challenge_tickets)
classes = model.classes_

for ticket, probability_row in zip(challenge_tickets, probabilities):
    best_index = probability_row.argmax()
    prediction = classes[best_index]
    confidence = probability_row[best_index]

    print(f"\nTicket: {ticket}")
    print(f"Prediction: {prediction}")
    print(f"Confidence: {confidence:.2%}")