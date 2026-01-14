import os
import json
import shutil
from datetime import datetime
from typing import Dict, List
from app.services.state_manager.base_history import BaseHistoryStore
from app import logger
import math
import numpy as np

class FileHistoryStore(BaseHistoryStore):
    """Store conversations as JSON files on disk with co-located uploads"""
    
    def __init__(self, storage_dir: str):
        """
        Initialize file-based history store.
        
        Args:
            storage_dir: Base directory where session folders will be created
                        Structure: {storage_dir}/{session_id}/messages.json
                                  {storage_dir}/{session_id}/uploads/
        """
        self.storage_dir = storage_dir
        self.metadata_file = os.path.join(storage_dir, "metadata.json")
        os.makedirs(storage_dir, exist_ok=True)
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from disk or create empty"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}
            self._save_metadata()
    
    def _save_metadata(self):
        """Persist metadata to disk"""
        try:
            sanitized = FileHistoryStore._sanitize_for_json(self.metadata)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(sanitized, f, indent=2, allow_nan=False)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _get_session_dir(self, session_id: str) -> str:
        """Get session directory path"""
        return os.path.join(self.storage_dir, session_id)
    
    def _get_session_file(self, session_id: str) -> str:
        """Get messages file path for a session"""
        return os.path.join(self._get_session_dir(session_id), "messages.json")
    
    def get_session_upload_dir(self, session_id: str) -> str:
        """Get uploads directory for a session"""
        return os.path.join(self._get_session_dir(session_id), "uploads")
    
    async def save_uploaded_files(self, session_id: str, files: list) -> List[str]:
        """Save uploaded files to session's upload directory, return file paths"""
        upload_dir = self.get_session_upload_dir(session_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        saved_paths = []
        for file in files:
            filepath = os.path.join(upload_dir, file.filename)
            content = await file.read()
            with open(filepath, 'wb') as f:
                f.write(content)
            saved_paths.append(filepath)
            logger.info(f"Saved uploaded file: {filepath}")
        
        # Update lightweight global index
        if session_id not in self.metadata:
            self.metadata[session_id] = {
                "created_at": datetime.now().isoformat(),
                "last_access": datetime.now().isoformat(),
                "message_count": 0,
                "has_files": True
            }
        else:
            self.metadata[session_id]["has_files"] = True
            self.metadata[session_id]["last_access"] = datetime.now().isoformat()
        self._save_metadata()

        # Update per-session metadata.json (co-located with messages.json)
        await self._save_session_metadata(session_id, file_paths=saved_paths, file_metadata=None)

        return saved_paths
    
    async def get_messages(self, session_id: str) -> List[Dict]:
        """Load messages from session file"""
        session_file = self._get_session_file(session_id)
        
        if not os.path.exists(session_file):
            return []
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Update last access
            if session_id in self.metadata:
                self.metadata[session_id]["last_access"] = datetime.now().isoformat()
                self._save_metadata()
            
            return messages
        except Exception as e:
            logger.error(f"Failed to load messages for session {session_id}: {e}")
            return []
    
    async def add_message(self, session_id: str, message: dict):
        """Add message to session file"""
        session_dir = self._get_session_dir(session_id)
        session_file = self._get_session_file(session_id)
        
        # Create session directory if it doesn't exist
        os.makedirs(session_dir, exist_ok=True)
        
        # Load existing messages or create new list
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    messages = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load existing messages for session {session_id}: {e}")
                messages = []
        else:
            messages = []
            # Initialize metadata for new session
            self.metadata[session_id] = {
                "created_at": datetime.now().isoformat(),
                "last_access": datetime.now().isoformat(),
                "message_count": 0,
                "has_files": False
            }
        
        # Add new message
        messages.append(message)
        
        # Save messages
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save messages for session {session_id}: {e}")
            return
        
        # Update metadata
        self.metadata[session_id]["last_access"] = datetime.now().isoformat()
        self.metadata[session_id]["message_count"] = len(messages)
        self._save_metadata()
        
        logger.debug(f"Added message to session {session_id}")
    
    async def clear_session(self, session_id: str):
        """Delete entire session directory (messages + uploads)"""
        session_dir = self._get_session_dir(session_id)
        
        # Remove entire session directory
        if os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
                logger.info(f"Deleted session directory: {session_dir}")
            except Exception as e:
                logger.error(f"Failed to delete session directory {session_dir}: {e}")
        
        # Remove metadata
        if session_id in self.metadata:
            del self.metadata[session_id]
            self._save_metadata()
    
    async def list_sessions(self) -> List[Dict]:
        """Return list of all sessions with metadata"""
        return [
            {"session_id": sid, **meta}
            for sid, meta in self.metadata.items()
        ]
    
    def _get_session_metadata_file(self, session_id: str) -> str:
        """Get metadata for specific session"""
        return os.path.join(self._get_session_dir(session_id), "metadata.json")
    
    @staticmethod
    def _sanitize_for_json(obj):
        # None stays None
        if obj is None:
            return None

        # Dict: recurse into values
        if isinstance(obj, dict):
            return {
                k: FileHistoryStore._sanitize_for_json(v)
                for k, v in obj.items()
            }

        # Iterable containers
        if isinstance(obj, (list, tuple, set)):
            return [
                FileHistoryStore._sanitize_for_json(v)
                for v in obj
            ]

        # NumPy handling (scalars + arrays)
        if np is not None:
            # NumPy scalar types (bool, int, float, etc.)
            if isinstance(obj, np.generic):
                value = obj.item()
                if isinstance(value, float) and math.isnan(value):
                    return None
                return value

            # NumPy arrays
            if isinstance(obj, np.ndarray):
                return FileHistoryStore._sanitize_for_json(obj.tolist())

        # Native float NaN
        if isinstance(obj, float) and math.isnan(obj):
            return None

        # Fallback: return as-is
        return obj


    async def save_session_metadata(self, session_id: str, file_paths: list = None, file_metadata: dict = None) -> None:
        await self._save_session_metadata(session_id, file_paths=file_paths, file_metadata=file_metadata)
    
    async def _save_session_metadata(self, session_id: str, file_paths: list = None, file_metadata: dict = None):
        session_meta_path = self._get_session_metadata_file(session_id)
        os.makedirs(self._get_session_dir(session_id), exist_ok=True)

        # Load existing session metadata if present
        session_data = {}
        if os.path.exists(session_meta_path):
            try:

                with open(session_meta_path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load existing session metadata for {session_id}: {e}")
                session_data = {}

        # Ensure base structure
        session_data.setdefault("file_paths", [])
        session_data.setdefault("file_metadata", {})
        session_data.setdefault("created_at", datetime.now().isoformat())
        session_data["last_access"] = datetime.now().isoformat()

        # Merge file_paths and metadata
        if file_paths:
            # preserve order, dedupe
            combined = session_data["file_paths"] + file_paths
            session_data["file_paths"] = list(dict.fromkeys(combined))
        if file_metadata:
            session_data["file_metadata"].update(file_metadata)

        try:
            sanitized = FileHistoryStore._sanitize_for_json(session_data)
            with open(session_meta_path, "w", encoding="utf-8") as f:
                json.dump(sanitized, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save session metadata for {session_id}: {e}")

    # Return per-session stored file paths (from conversations/{session_id}/metadata.json)
    async def get_uploaded_file_paths(self, session_id: str) -> List[str]:
        session_meta_path = self._get_session_metadata_file(session_id)
        if not os.path.exists(session_meta_path):
            return []
        try:
            with open(session_meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("file_paths", [])
        except Exception as e:
            logger.error(f"Failed to load uploaded file paths for session {session_id}: {e}")
            return []  


    async def get_session_metadata(self, session_id: str) -> Dict:
        # Start with the global index entry (created_at, last_access, message_count, has_files)
        global_meta = self.metadata.get(session_id, {}).copy()

        # Load per-session metadata if present and merge
        session_meta_path = self._get_session_metadata_file(session_id)
        if os.path.exists(session_meta_path):
            try:
                with open(session_meta_path, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                # merge file_paths and file_metadata into returned metadata
                if "file_paths" in session_data:
                    global_meta["file_paths"] = session_data["file_paths"]
                if "file_metadata" in session_data:
                    global_meta["file_metadata"] = session_data["file_metadata"]
                # keep created_at/last_access from session file if it's more accurate
                global_meta.setdefault("created_at", session_data.get("created_at"))
                global_meta["last_access"] = session_data.get("last_access", global_meta.get("last_access"))
            except Exception as e:
                logger.error(f"Failed to load per-session metadata for {session_id}: {e}")
        return global_meta     
         