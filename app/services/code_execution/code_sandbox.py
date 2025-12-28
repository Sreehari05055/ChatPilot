# sandbox.py
import subprocess
import tempfile
import sys
import os
import traceback
from app.core.config import Config

class CodeSandboxExecutor:

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

            proc = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=Config.HTTP_TIMEOUT)

            success = proc.returncode == 0
            return {
                'success': success,
                'result': proc.stdout.strip() if success else None,
                'error': proc.stderr.strip() if not success else None,
                'returncode': proc.returncode,
            }

        except subprocess.TimeoutExpired as e:
            return {'success': False, 'result': None, 'error': f'Timeout after {Config.HTTP_TIMEOUT}s: {e}', 'returncode': None}
        except Exception as e:
            return {'success': False, 'result': None, 'error': str(e)}
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
