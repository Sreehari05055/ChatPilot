# sandbox.py
import subprocess
import tempfile
import sys
import os
import traceback
from app.core.config import Config

class CodeSandboxExecutor:

    def __init__(self, error_classifier):
        self.error_classifier = error_classifier

    def execute_code(self, code: str) -> dict:
        """Execute the given Python `code` in a subprocess using a temporary file.

        Returns a dict with keys: `success` (bool), `result` (stdout string or None),
        `error` (stderr or exception traceback), and `returncode` (int or None).
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False, encoding='utf-8') as tf:
                tf.write(code)
                tf.flush()
                tmp_path = tf.name

            proc = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=Config.HTTP_TIMEOUT)

            success = proc.returncode == 0
            if success:
                return {
                    'success': success,
                    'result': proc.stdout.strip(),
                    'error': None,
                    'returncode': proc.returncode,
                }
            error_obj = self.error_classifier.classify_error(proc.stderr, proc.returncode)
            return {"success": False, "result": None, "error": error_obj, "returncode": proc.returncode}
        
        except subprocess.TimeoutExpired as e:
            error_obj = self.error_classifier.classify_error(
                stderr=f"Timeout after {Config.HTTP_TIMEOUT}s: {e}",
                returncode=None
            )
            return {"success": False, "result": None, "error": error_obj}

        except Exception as e:
            error_obj = self.error_classifier.classify_error(
                stderr=str(e),
                returncode=None
            )
            return {"success": False, "result": None, "error": error_obj}
        
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
