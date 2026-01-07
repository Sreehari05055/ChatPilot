import os
import json
import shutil
from datetime import datetime
from typing import Dict, List
from app.services.state_manager.base_history import BaseHistoryStore
from app import logger


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
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
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
        
        # Mark session has files in metadata
        if session_id in self.metadata:
            self.metadata[session_id]["has_files"] = True
            self._save_metadata()
        
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
    
    async def get_session_metadata(self, session_id: str) -> Dict:
        """Get metadata for specific session"""
        return self.metadata.get(session_id, {})
    
    def mark_session_has_files(self, session_id: str):
        """Mark that session has uploaded files"""
        if session_id not in self.metadata:
            # Create metadata if it doesn't exist yet
            self.metadata[session_id] = {
                "created_at": datetime.now().isoformat(),
                "last_access": datetime.now().isoformat(),
                "message_count": 0,
                "has_files": True
            }
        else:
            self.metadata[session_id]["has_files"] = True
        self._save_metadata()
