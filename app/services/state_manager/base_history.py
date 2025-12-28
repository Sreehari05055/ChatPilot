from abc import ABC, abstractmethod

class BaseHistoryStore(ABC):
    @abstractmethod
    async def get_messages(self, session_id: str) -> list[dict]:
        pass

    @abstractmethod
    async def add_message(self, session_id: str, message: dict):
        pass