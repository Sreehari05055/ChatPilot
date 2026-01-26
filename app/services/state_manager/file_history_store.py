from app.services.state_manager.base_history import BaseHistoryStore
from app import logger
import math
import numpy as np
import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

class FileHistoryStore(BaseHistoryStore):
    """
    Store conversations as JSON files on disk.
    - Global index: {storage_dir}/metadata.json (for listing sessions quickly)
    - Session data: {storage_dir}/{session_id}/
        - messages.json: Chat history
        - metadata.json: Session-specific info (files, analysis)
        - uploads/: Physical file storage
    """
    
    def __init__(self, storage_dir: str, rag_dir: str = "source_files"):
        self.storage_dir = storage_dir
        self.rag_dir = rag_dir
        self.global_metadata_file = os.path.join(storage_dir, "metadata.json")
        
        os.makedirs(storage_dir, exist_ok=True)
        os.makedirs(rag_dir, exist_ok=True)
        
        self.global_index = self._load_global_index()

    # --- Internal Helpers ---

    def _load_global_index(self) -> Dict[str, Any]:
        """Load the global session index from disk."""
        if os.path.exists(self.global_metadata_file):
            try:
                with open(self.global_metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load global index: {e}")
        return {}

    def _save_global_index(self):
        """Persist the global session index to disk."""
        try:
            with open(self.global_metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.global_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save global index: {e}")

    def _get_session_dir(self, session_id: str) -> str:
        return os.path.join(self.storage_dir, session_id)

    def _get_messages_file(self, session_id: str) -> str:
        return os.path.join(self._get_session_dir(session_id), "messages.json")

    def _get_session_metadata_file(self, session_id: str) -> str:
        return os.path.join(self._get_session_dir(session_id), "metadata.json")

    def _ensure_session(self, session_id: str):
        """Ensure session directory and global index entry exist."""
        os.makedirs(self._get_session_dir(session_id), exist_ok=True)
        if session_id not in self.global_index:
            self.global_index[session_id] = {
                "created_at": datetime.now().isoformat(),
                "last_access": datetime.now().isoformat(),
                "message_count": 0,
                "has_files": False
            }
            self._save_global_index()

    def _sanitize_for_json(self, obj: Any) -> Any:
        """Handle non-serializable types (NaN, NumPy types) for JSON storage."""
        if obj is None: return None
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [self._sanitize_for_json(v) for v in obj]
        
        if isinstance(obj, float) and math.isnan(obj):
            return None
            
        # Handle NumPy types if present
        if hasattr(obj, "item"): # NumPy scalars
            val = obj.item()
            return None if isinstance(val, float) and math.isnan(val) else val
        if hasattr(obj, "tolist"): # NumPy arrays
            return self._sanitize_for_json(obj.tolist())
            
        return obj

    # --- BaseHistoryStore Implementation ---

    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        msg_file = self._get_messages_file(session_id)
        if not os.path.exists(msg_file):
            return []
        
        try:
            with open(msg_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            # Update last access in global index
            if session_id in self.global_index:
                self.global_index[session_id]["last_access"] = datetime.now().isoformat()
                self._save_global_index()
                
            return messages
        except Exception as e:
            logger.error(f"Error loading messages for {session_id}: {e}")
            return []

    async def add_message(self, session_id: str, message: Dict[str, Any]):
        self._ensure_session(session_id)
        messages = await self.get_messages(session_id)
        messages.append(message)
        
        try:
            with open(self._get_messages_file(session_id), 'w', encoding='utf-8') as f:
                json.dump(messages, f, indent=2, ensure_ascii=False)
            
            # Sync global index
            self.global_index[session_id]["last_access"] = datetime.now().isoformat()
            self.global_index[session_id]["message_count"] = len(messages)
            self._save_global_index()
        except Exception as e:
            logger.error(f"Error adding message to {session_id}: {e}")

    async def clear_session(self, session_id: str):
        session_dir = self._get_session_dir(session_id)
        if os.path.exists(session_dir):
            try:
                shutil.rmtree(session_dir)
            except Exception as e:
                logger.error(f"Error deleting session dir {session_id}: {e}")
        
        if session_id in self.global_index:
            del self.global_index[session_id]
            self._save_global_index()

    async def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {"session_id": sid, **meta}
            for sid, meta in self.global_index.items()
        ]

    async def get_session_metadata(self, session_id: str) -> Dict[str, Any]:
        # Start with global info
        data = self.global_index.get(session_id, {}).copy()
        
        # Merge with local metadata if exists
        meta_file = self._get_session_metadata_file(session_id)
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    local_data = json.load(f)
                data.update(local_data)
            except Exception as e:
                logger.error(f"Error loading local metadata for {session_id}: {e}")
        
        return data

    async def save_session_metadata(self, session_id: str, file_paths: Optional[List[str]] = None, file_metadata: Optional[Dict[str, Any]] = None) -> None:
        self._ensure_session(session_id)
        meta_file = self._get_session_metadata_file(session_id)
        
        # Load existing
        current = {}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    current = json.load(f)
            except: pass

        # Update file_paths (Store only basenames)
        if file_paths:
            existing_names = current.get("file_paths", [])
            new_names = [os.path.basename(p) for p in file_paths]
            combined = existing_names + new_names
            current["file_paths"] = list(dict.fromkeys(combined)) # Dedupe
            
        # Update file_metadata (Keys should be basenames)
        if file_metadata:
            clean_metadata = {os.path.basename(k): v for k, v in file_metadata.items()}
            current.setdefault("file_metadata", {}).update(clean_metadata)
        
        current["last_updated"] = datetime.now().isoformat()
        
        # Persist
        try:
            sanitized = self._sanitize_for_json(current)
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(sanitized, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving session metadata for {session_id}: {e}")

    # --- File Management Implementation ---

    def get_session_upload_dir(self, session_id: str) -> str:
        return os.path.join(self._get_session_dir(session_id), "uploads")

    async def get_uploaded_file_paths(self, session_id: str) -> List[str]:
        metadata = await self.get_session_metadata(session_id)
        return metadata.get("file_paths", [])

    async def save_uploaded_files(self, session_id: str, files: List[Any]) -> List[str]:
        upload_dir = self.get_session_upload_dir(session_id)
        os.makedirs(upload_dir, exist_ok=True)
        
        saved_paths = []
        for file in files:
            filepath = os.path.join(upload_dir, file.filename)
            content = await file.read()
            with open(filepath, 'wb') as f:
                f.write(content)
            saved_paths.append(filepath)
            logger.info(f"Saved session file: {filepath}")
        
        # Sync metadata
        self._ensure_session(session_id)
        self.global_index[session_id]["has_files"] = True
        self._save_global_index()
        
        await self.save_session_metadata(session_id, file_paths=saved_paths)
        return saved_paths

    # --- RAG Corpus Management ---

    def get_rag_dir(self) -> str:
        return self.rag_dir

    async def list_rag_files(self) -> List[Dict[str, Any]]:
        files = []
        for filename in os.listdir(self.rag_dir):
            filepath = os.path.join(self.rag_dir, filename)
            if os.path.isfile(filepath):
                stats = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "path": filepath,
                    "size": stats.st_size,
                    "modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
                })
        return files

    async def save_rag_file(self, file: Any) -> str:
        filepath = os.path.join(self.rag_dir, file.filename)
        content = await file.read()
        with open(filepath, 'wb') as f:
            f.write(content)
        logger.info(f"Saved RAG corpus file: {filepath}")
        return filepath

    async def delete_rag_file(self, filename: str) -> None:
        filepath = os.path.join(self.rag_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted RAG corpus file: {filepath}")
     
         