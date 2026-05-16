from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    @abstractmethod
    def call(self, method: str, params: dict) -> dict:
        pass
