import sys
from pathlib import Path

import httpx
from google import genai
from google.genai import errors, types


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "apps"))

from backend.database import settings


def main() -> int:
    api_key = (
        settings.gemini_api_key
        .get_secret_value()
        .strip()
    )

    if not api_key:
        print("MISSING_API_KEY")
        return 1

    try:
        with genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=settings.billing_ai_timeout_ms,
                retry_options=types.HttpRetryOptions(
                    attempts=1,
                ),
            ),
        ) as client:
            names = sorted(
                model.name
                for model in client.models.list()
                if model.name
                and "generateContent"
                in (model.supported_actions or [])
            )

    except errors.APIError as error:
        print(
            "MODEL_LIST_FAILED:",
            "status_code=",
            error.code,
        )
        return 1

    except (TimeoutError, httpx.TimeoutException):
        print("CONNECTION_TIMEOUT")
        return 1

    except httpx.RequestError:
        print("CONNECTION_ERROR")
        return 1

    print("Connection OK")
    print("Models supporting generateContent:")

    for name in names:
        print(name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())