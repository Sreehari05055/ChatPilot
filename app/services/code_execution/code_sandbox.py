# code_sandbox.py
import docker
import threading
import time
import os
import io
import tarfile
from typing import Optional, List
from app import logger
from app.core.config import Config

class CodeSandboxExecutor:
    """
    Execute Python code in an isolated Docker container for security.
    Uses a persistent container to minimize latency but ensures file isolation.
    """
    
    def __init__(self, error_classifier, image_name: str = "python-sandbox:latest"):
        self.error_classifier = error_classifier
        self.image_name = image_name
        self.client = None
        self.containers = {}
        self._lock = threading.Lock()
        # Load sandbox limits from config (allow runtime changes via env)
        try:
            self.sandbox_nano_cpus = getattr(Config, 'SANDBOX_NANO_CPUS', 500000000)
            self.sandbox_mem_limit = getattr(Config, 'SANDBOX_MEM_LIMIT', '512m')
            self.sandbox_mem_reservation = getattr(Config, 'SANDBOX_MEM_RESERVATION', '256m')
            self.sandbox_memswap_limit = getattr(Config, 'SANDBOX_MEMSWAP_LIMIT', self.sandbox_mem_limit)
            self.sandbox_pids_limit = getattr(Config, 'SANDBOX_PIDS_LIMIT', 64)
            self.sandbox_shm_size = getattr(Config, 'SANDBOX_SHM_SIZE', '64m')
            self.sandbox_auto_remove = getattr(Config, 'SANDBOX_AUTO_REMOVE', False)
        except Exception:
            # Fallbacks in case Config is missing attributes
            self.sandbox_nano_cpus = 500000000
            self.sandbox_mem_limit = '512m'
            self.sandbox_mem_reservation = '256m'
            self.sandbox_memswap_limit = '512m'
            self.sandbox_pids_limit = 64
            self.sandbox_shm_size = '64m'
            self.sandbox_auto_remove = False

        self._initialize()
    
    def _initialize(self):
        """Initialize Docker client and ensure container is running."""
        try:
            self.client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            # We don't raise here to allow the app to start even if Docker is down
            # but execution will fail later with a clear message.
    
    def _ensure_container(self, session_id: str):
        """Ensure the sandbox container is running."""
        if not self.client:
            return
        container_name = f"chatpilot-sandbox-{session_id}"
        with self._lock:
            if session_id in self.containers:
                return self.containers[session_id]
            try:
                container = self.client.containers.get(container_name)
                if container.status != 'running':
                    logger.info(f"Starting stopped container: {container_name}")
                    container.start()
                self.containers[session_id] = container
                return container
            except docker.errors.NotFound:
                logger.info(f"Creating new container: {container_name}")
                container = self._create_container(container_name)
                self.containers[session_id] = container
                return container
    
    def _create_container(self, container_name: str):
        """Create a new sandbox container."""
        try:
            # Enable read-only access to the data directory for large file analysis
            host_data_path = os.path.abspath(Config.DATA_DIR)
            volumes = {
                host_data_path: {
                    'bind': '/home/sandboxuser/data',
                    'mode': 'ro'
                }
            }

            container = self.client.containers.run(
                image=self.image_name,
                name=container_name,
                detach=True,
                command="sleep infinity",
                user="sandboxuser",
                network_mode="none",
                volumes=volumes,
                # Apply configurable resource limits
                mem_limit=self.sandbox_mem_limit,
                mem_reservation=self.sandbox_mem_reservation,
                memswap_limit=self.sandbox_memswap_limit,
                nano_cpus=self.sandbox_nano_cpus,
                pids_limit=self.sandbox_pids_limit,
                shm_size=self.sandbox_shm_size,
                auto_remove=self.sandbox_auto_remove,
            )
            time.sleep(1) # Wait for startup
            return container
        except Exception as e:
            if "unable to find user sandboxuser" in str(e):
                logger.error("CRITICAL: The Docker image 'python-sandbox:latest' does not have a 'sandboxuser'.")
                logger.error("Please run: docker build -t python-sandbox:latest -f sandbox.Dockerfile .")
            else:
                logger.error(f"Failed to create Docker container: {e}")
            raise

    def _copy_files_to_container(self, container, file_paths: List[str]):
        """Copy local files into the container's working directory."""
        if not file_paths:
            return
        
        # Create a tar buffer in memory
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            for path in file_paths:
                if os.path.exists(path):
                    tar.add(path, arcname=os.path.basename(path))
        
        tar_stream.seek(0)
        container.put_archive('/home/sandboxuser', tar_stream)

    def execute_code(self, code: str, session_id: str, file_paths: List[str] = None) -> dict:
        """
        Execute Python code in the Docker container.
        """
        if not self.client:
            return {
                "success": False,
                "error": {"message": "Docker not available", "category": "CONFIG_ERROR"},
                "result": None
            }
        
        container = self._ensure_container(session_id)
        
        # 1. Identify which files need to be copied (Session uploads) vs just referenced (Global data)
        abs_data_dir = os.path.abspath(Config.DATA_DIR).lower()
        files_to_copy = []
        
        if file_paths:
            for path in file_paths:
                abs_path = os.path.abspath(path)
                # If it's NOT in the mounted DATA_DIR, we must copy it manually
                if not abs_path.lower().startswith(abs_data_dir):
                    files_to_copy.append(abs_path)
            
            if files_to_copy:
                self._copy_files_to_container(container, files_to_copy)

        # 2. Path Translation Magic:
        # We replace absolute host paths in the agent's code with container paths.
        if file_paths:
            for path in file_paths:
                filename = os.path.basename(path)
                abs_path = os.path.abspath(path)
                
                # Case A: Global file in 'source_files/' -> 'data/filename'
                if abs_path.lower().startswith(abs_data_dir):
                    target_path = f"data/{filename}"
                # Case B: Session file in 'uploads/' -> 'filename'
                else:
                    target_path = filename
                
                # Replace exact and escaped variations of the path
                code = code.replace(path, target_path)
                code = code.replace(path.replace('\\', '\\\\'), target_path)
                code = code.replace(path.replace('\\', '/'), target_path)

        try:
            # 3. Run code
            exec_result = container.exec_run(
                cmd=['python', '-c', code],
                demux=True,
                user='sandboxuser',
                workdir='/home/sandboxuser',
            )

            stdout = exec_result.output[0].decode('utf-8', errors='replace') if exec_result.output[0] else ''
            stderr = exec_result.output[1].decode('utf-8', errors='replace') if exec_result.output[1] else ''
            returncode = exec_result.exit_code

            if returncode == 0:
                result = stdout.strip() or stderr.strip()
                return {'success': True, 'result': result, 'error': None, 'returncode': 0}
            
            error_obj = self.error_classifier.classify_error(stderr, returncode)
            error_msg = error_obj.get("message") or "Unknown execution error"
            return {
                "success": False, 
                "result": None, 
                "error": error_msg, 
                "error_details": error_obj, 
                "returncode": returncode
            }

        except Exception as e:
            logger.error(f"Docker execution failed: {e}")
            return {"success": False, "result": None, "error": str(e)}
