import argparse
import json
import sys
from pathlib import Path

import httpx
from google.genai import errors
from pydantic import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps"))

from backend.ai.provider import call_gemini_billing


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Send one live Gemini billing request "
            "using synthetic data only."
        )
    )
    parser.add_argument(
        "--scenario",
        choices=("single", "duplicate"),
        default="single",
    )
    args = parser.parse_args()

    if args.scenario == "duplicate":
        payment_evidence = {
            "payment_ids": [101, 102],
            "has_possible_duplicate": True,
            "successful_payment_count": 2,
        }
    else:
        payment_evidence = {
            "payment_ids": [101],
            "has_possible_duplicate": False,
            "successful_payment_count": 1,
        }

    policies = [
        {
            "id": 201,
            "title": "Synthetic duplicate-charge review policy",
            "text": (
                "A possible duplicate payment must be reviewed "
                "using verified payment records. "
                "A refund requires approval from an "
                "authorized human administrator. "
                "Insufficient evidence must not be described "
                "as a confirmed duplicate payment."
            ),
        },
        {
            "id": 202,
            "title": "Synthetic product-return policy",
            "text": (
                "For ordinary product returns, unused items "
                "may be returned within 14 days of purchase. "
                "This excerpt does not specify conditions "
                "for duplicate-charge investigation."
            ),
        },
    ]

    ticket_text = (
        "Synthetic test: I believe I may have been charged "
        "twice for this order. Please investigate the "
        "possible duplicate charge. "
        "This is not a product-return request."
    )

    print(
        "Sending one live Gemini request "
        f"with synthetic data only. Scenario: {args.scenario}"
    )

    try:
        result = call_gemini_billing(
            payment_evidence=payment_evidence,
            policies=policies,
            ticket_text=ticket_text,
        )

    except ValidationError:
        print("FAILED: INVALID_PROVIDER_OUTPUT")
        return 1

    except errors.APIError as error:
        print(
            "FAILED: PROVIDER_API_ERROR",
            "status_code=",
            error.code,
        )
        return 1

    except (TimeoutError, httpx.TimeoutException):
        print("FAILED: PROVIDER_TIMEOUT")
        return 1

    except httpx.RequestError:
        print("FAILED: PROVIDER_CONNECTION_ERROR")
        return 1

    except ValueError as error:
        safe_codes = {
            "MISSING_API_KEY",
            "MISSING_MODEL",
            "NO_CANDIDATE",
            "INCOMPLETE_OR_BLOCKED_OUTPUT",
            "EMPTY_OUTPUT",
            "INVALID_EVIDENCE_IDS",
            "INVALID_POLICY_IDS",
        }

        code = str(error)

        if code not in safe_codes:
            code = "INVALID_PROVIDER_OUTPUT"

        print("FAILED:", code)
        return 1

    print("LIVE_RESPONSE_VALIDATED")
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )

    print(
        "\nManual review required: schema and ID validation "
        "do not prove semantic correctness."
    )
    print(
        "- Findings must remain limited to the selected order."
    )
    print(
        "- A possible duplicate must not be called confirmed."
    )
    print(
        "- The product-return window must not be imposed "
        "on duplicate-charge investigation."
    )
    print(
        "- No completed refund or investigation "
        "should be claimed."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())