
import os
from app.services.code_execution.file_handler_factory import FileHandlerFactory
from app.services.code_execution.code_generator import CodeGenerator
from app.services.code_execution.code_sandbox import CodeSandboxExecutor
from app.services.code_execution.base_handler_factory import BaseFileHandler
from app import logger
from app.core.config import Config

class CodeExecutionService:
    def __init__(self, llm_engine):
        self.llm_engine = llm_engine
        self.code_generator = CodeGenerator(self.llm_engine)
        self.code_executor = CodeSandboxExecutor()

    async def analyze_files(self, filepaths: list) -> dict:
        """Analyze uploaded files, return metadata."""
        results = {}
        for filepath in filepaths:
            handler = FileHandlerFactory.get_handler(filepath)
            metadata = handler.analyze_file(filepath)
            filename = os.path.basename(filepath)
            results[filename] = metadata
        return results
    
    async def generate_solution(self, task_todo: str, metadata: dict) -> dict:
        """Generate solution using Python code for the given task using LLM."""
        
        previous_code = None
        previous_error = None

        for attempt in range(1, Config.MAX_RETRIES + 1):
            logger.info(f"Code generation attempt {attempt}/{Config.MAX_RETRIES}")
        
            try:
                code_response = await self.code_generator.generate_code(task_todo, metadata, previous_code, previous_error)

                cleaned_code = BaseFileHandler.clean_code_block(code_response)
                
                execution_result = self.code_executor.execute_code(cleaned_code)
                logger.debug(f"Execution result: {execution_result}")
                if execution_result['success']:
                    logger.info(f"✅ Success on attempt {attempt}")
                    return {
                        'success': True,
                        'result': execution_result['result'],
                        'code': cleaned_code,
                        'attempts': attempt
                    }
                else:
                    # Failed - prepare for retry
                    previous_code = cleaned_code
                    previous_error = execution_result['error']
                    logger.warning(f"❌ Attempt {attempt} failed: {previous_error}")
            
            except Exception as e:
                logger.error(f"Error in attempt {attempt}: {e}")
                previous_error = str(e)                 

        logger.error(f"All {Config.MAX_RETRIES} attempts failed")
        return {
            'success': False,
            'error': f"Failed after {Config.MAX_RETRIES} attempts. Last error: {previous_error}",
            'attempts': Config.MAX_RETRIES
        }