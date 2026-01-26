from app import logger

class ErrorKeyWords:

    NON_RETRYABLE_ERRORS = (
    "APIKeyError",
    "PermissionError",
    "Timeout",
    "EnvironmentError",
    "NetworkError",
    )
    RETRYABLE_ERRORS = (
        "SyntaxError",
        "IndentationError",
        "TypeError",
        "ValueError",
        "ZeroDivisionError",
    )

class ErrorClassifier:
    @staticmethod
    def classify_error(stderr: str | None, returncode: int | None) -> dict:
        """
        Convert a raw error string into a structured error with category, retryable flag, and confidence.
        """
        # --- Handle Docker/OS Specific Exit Codes ---
        if returncode == 137:
            return {
                "message": "Out of Memory (OOM): The sandbox was killed because it exceeded its memory limit. Try processing the data in chunks or optimizing memory usage.",
                "category": "NON_RETRYABLE",
                "retryable": False,
                "returncode": 137,
            }

        if not stderr:
            if returncode and returncode != 0:
                return {
                    "message": f"Execution failed with return code {returncode} and no error output.",
                    "category": "UNKNOWN",
                    "retryable": True,
                    "returncode": returncode,
                }
            return {
                "message": "Unknown error occurred during execution.",
                "category": "UNKNOWN",
                "retryable": True,
                "returncode": returncode,
            }

        if any(k in stderr for k in ErrorKeyWords.NON_RETRYABLE_ERRORS):
            return {
                "message": stderr.strip(),
                "category": "NON_RETRYABLE",
                "retryable": False,
                "returncode": returncode,
            }

        if any(k in stderr for k in ErrorKeyWords.RETRYABLE_ERRORS):
            return {
                "message": stderr.strip(),
                "category": "RETRYABLE",
                "retryable": True,
                "returncode": returncode,
            }

        # Fallback for unknown errors
        return {
            "message": stderr.strip(),
            "category": "UNKNOWN",
            "retryable": True,
            "returncode": returncode,
        }