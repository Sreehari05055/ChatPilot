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
    def classify_error(stderr: str | None, returncode: int | None) -> dict | None:
        """
        Convert a raw error string into a structured error with category, retryable flag, and confidence.
        """
        if not stderr:
            return None

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