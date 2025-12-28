from app.services.state_manager.base_history import BaseHistoryStore

class InMemoryStore(BaseHistoryStore):
    def __init__(self):
        self._storage = {}

    async def get_messages(self, session_id: str):
        return self._storage.get(session_id, [])

    async def add_message(self, session_id: str, message: dict):
        if session_id not in self._storage:
            self._storage[session_id] = []
        self._storage[session_id].append(message)