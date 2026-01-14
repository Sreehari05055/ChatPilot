from abc import ABC, abstractmethod
from typing import List

class BaseHistoryStore(ABC):
    @abstractmethod
    async def get_messages(self, session_id: str) -> list[dict]:
        pass

    @abstractmethod
    async def add_message(self, session_id: str, message: dict):
        pass

    @abstractmethod
    async def clear_session(self, session_id: str): pass
    
    @abstractmethod
    async def list_sessions(self) -> list: pass
    
    @abstractmethod
    async def get_session_metadata(self, session_id: str) -> dict: pass
    
    @abstractmethod
    def get_session_upload_dir(self, session_id: str) -> str:
        """Get directory where session files are stored"""
        pass
    @abstractmethod
    async def get_session_metadata(self, session_id: str) -> dict:
        """Get stored file metadata for a session"""
        pass
    @abstractmethod
    async def get_uploaded_file_paths(self, session_id: str) -> List[str]:
        """Get list of uploaded file paths for a session"""
        pass
    
    @abstractmethod
    async def save_uploaded_files(self, session_id: str, files: list) -> List[str]:
        """Save uploaded files to session storage, return file paths"""
        pass
    
    @abstractmethod
    async def save_session_metadata(self, session_id: str, file_paths: list = None, file_metadata: dict = None) -> None:
        """Save session metadata including file paths and file metadata"""
        pass
