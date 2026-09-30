from backend.ml.service import suggest_ticket_category


result = suggest_ticket_category(
    subject="Subscription not upgraded",
    description=(
        "My card payment succeeded, but I still cannot access "
        "the premium features."
    ),
)

print(result)