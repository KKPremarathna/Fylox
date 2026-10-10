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
    payment_evidence = {
        "payment_ids": [101, 102],
        "has_possible_duplicate": False,
        "successful_payment_count": 1,
    }

    policies = [
        {
            "id": 201,
            "title": "Synthetic billing review policy",
            "text": (
                "A possible duplicate payment must be reviewed "
                "using verified payment records. "
                "A refund requires approval from an "
                "authorized human administrator. "
                "Insufficient evidence must not be described "
                "as a confirmed duplicate payment."
            ),
        }
    ]

    print(
        "Sending one live Gemini request "
        "with synthetic data only."
    )

    try:
        result = call_gemini_billing(
            payment_evidence=payment_evidence,
            policies=policies,
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())