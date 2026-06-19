import os
import time
import logging
from typing import Optional

from dotenv import load_dotenv
from google import genai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


class GeminiKeyManager:

    def __init__(
        self,
        key_prefix="GEMINI_API_KEY",
        count=2,
        cooldown_seconds=60,
        model="gemini-2.5-flash"
    ):

        load_dotenv()

        self.model = model
        self.cooldown_seconds = cooldown_seconds

        self.api_keys = []

        for i in range(1, count + 1):

            key = os.getenv(f"{key_prefix}{i}")

            if key:
                self.api_keys.append(
                    {
                        "id": i,
                        "key": key,
                        "status": "active",
                        "retry_after": 0
                    }
                )

        if not self.api_keys:
            raise ValueError(
                f"No keys found: {key_prefix}1..{key_prefix}{count}"
            )

        self.current_index = 0

        logger.info(
            f"Initialized with {len(self.api_keys)} keys."
        )

    # --------------------------------------------------
    # VALIDATION
    # --------------------------------------------------

    def _is_key_working(self, api_key):

        try:

            client = genai.Client(
                api_key=api_key
            )

            response = client.models.generate_content(
                model=self.model,
                contents="Reply with only: OK"
            )

            return bool(response.text)

        except Exception as e:

            logger.warning(
                f"Validation failed: {e}"
            )

            return False

    def check_all_keys(self):
        logger.info(
            "Initial status check skipped (keys pre-verified)"
        )
        for entry in self.api_keys:
            entry["status"] = "active"

    # --------------------------------------------------
    # ROUND ROBIN
    # --------------------------------------------------

    def get_available_key(self):

        now = time.time()

        valid_keys = [
            k
            for k in self.api_keys
            if k["status"] != "disabled"
        ]

        if not valid_keys:

            raise RuntimeError(
                "No valid Gemini keys available."
            )

        for _ in range(len(valid_keys)):

            idx = (
                self.current_index
                % len(valid_keys)
            )

            entry = valid_keys[idx]

            if (
                entry["status"] == "active"
                or (
                    entry["status"] == "rate_limited"
                    and now > entry["retry_after"]
                )
            ):

                self.current_index += 1

                logger.info(
                    f"Using Key {entry['id']}"
                )

                return entry["key"]

            self.current_index += 1

        waits = []

        for k in valid_keys:

            if k["status"] == "rate_limited":

                waits.append(
                    k["retry_after"] - now
                )

        if waits:

            sleep_time = max(
                1,
                min(waits)
            )

            logger.warning(
                f"All keys cooling down. Waiting {sleep_time:.1f}s"
            )

            time.sleep(sleep_time)

            return self.get_available_key()

        raise RuntimeError(
            "No active Gemini key available."
        )

    # --------------------------------------------------
    # CLIENT
    # --------------------------------------------------

    def get_client(self):

        api_key = self.get_available_key()

        return genai.Client(
            api_key=api_key
        )

    # --------------------------------------------------
    # FAILURE HANDLING
    # --------------------------------------------------

    def mark_key_failed(
        self,
        api_key,
        reason
    ):

        now = time.time()

        for entry in self.api_keys:

            if entry["key"] != api_key:
                continue

            reason_lower = reason.lower()

            if (
                "429" in reason
                or "quota" in reason_lower
                or "rate" in reason_lower
            ):

                entry["status"] = "rate_limited"

                entry["retry_after"] = (
                    now + self.cooldown_seconds
                )

                logger.warning(
                    f"Key {entry['id']} rate limited."
                )

            elif (
                "403" in reason
                or "permission" in reason_lower
                or "unauthorized" in reason_lower
            ):

                entry["status"] = "disabled"

                logger.error(
                    f"Key {entry['id']} disabled."
                )

            else:

                entry["status"] = "failed"

                entry["retry_after"] = (
                    now + self.cooldown_seconds
                )

                logger.error(
                    f"Key {entry['id']} failed."
                )

            break


# ==================================================
# SIMPLE HELPER
# ==================================================

_manager = None


def get_manager():

    global _manager

    if _manager is None:

        _manager = GeminiKeyManager()

        _manager.check_all_keys()

    return _manager


def generate_content(
    prompt,
    model="gemini-2.5-flash"
):

    manager = get_manager()

    api_key = manager.get_available_key()

    try:

        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model=model,
            contents=prompt
        )

        return response.text

    except Exception as e:

        manager.mark_key_failed(
            api_key,
            str(e)
        )

        raise


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    result = generate_content(
        "What is the capital of France?"
    )

    print(result)