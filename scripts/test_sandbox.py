import os
import sys
from pathlib import Path

# Add the project root to sys.path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.services.code_execution.code_sandbox import CodeSandboxExecutor
from app.services.code_execution.error_classifier import ErrorClassifier

def test_sandbox():
    classifier = ErrorClassifier()
    executor = CodeSandboxExecutor(classifier)
    
    code = "print('Hello from Sandbox!')"
    session_id = "test-session"
    
    print(f"Executing simple code: {code}")
    result = executor.execute_code(code, session_id)
    print(f"Result: {result}")

    code_with_error = "print(1/0)"
    print(f"\nExecuting code with error: {code_with_error}")
    result = executor.execute_code(code_with_error, session_id)
    print(f"Result: {result}")

if __name__ == "__main__":
    test_sandbox()
