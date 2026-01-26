from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any

class BaseHistoryStore(ABC):
    @abstractmethod
    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages for a specific session."""
        pass

    @abstractmethod
    async def add_message(self, session_id: str, message: Dict[str, Any]):
        """Add a single message to the session history."""
        pass

    @abstractmethod
    async def clear_session(self, session_id: str):
        """Delete all history and associated data (including uploads) for a session."""
        pass
    
    @abstractmethod
    async def list_sessions(self) -> List[Dict[str, Any]]:
        """Return a list of all active sessions with their basic metadata."""
        pass
    
    @abstractmethod
    async def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        """Get combined metadata for a session, including message info and file-related metadata."""
        pass

    @abstractmethod
    async def save_session_metadata(self, session_id: str, file_paths: Optional[List[str]] = None, file_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Save or update session-specific metadata (e.g., file paths, analyzed data schema)."""
        pass

    @abstractmethod
    def get_session_upload_dir(self, session_id: str) -> str:
        """Get directory path where session files are stored on disk."""
        pass

    @abstractmethod
    async def get_uploaded_file_paths(self, session_id: str) -> List[str]:
        """Get list of absolute paths for all uploaded files in a session."""
        pass
    
    @abstractmethod
    async def save_uploaded_files(self, session_id: str, files: List[Any]) -> List[str]:
        """Save uploaded files to session storage and return their resulting paths."""
        pass

    # --- RAG Corpus Management ---

    @abstractmethod
    def get_rag_dir(self) -> str:
        """Get directory path where global RAG corpus files are stored."""
        pass

    @abstractmethod
    async def list_rag_files(self) -> List[Dict[str, Any]]:
        """List all files currently in the global RAG corpus."""
        pass

    @abstractmethod
    async def save_rag_file(self, file: Any) -> str:
        """Save a new file to the global RAG corpus and return its path."""
        pass

    @abstractmethod
    async def delete_rag_file(self, filename: str) -> None:
        """Remove a file from the global RAG corpus."""
        pass
