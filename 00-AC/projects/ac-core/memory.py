class ShortTermMemory:
    def __init__(self, capacity: int = 10):
        self.capacity = capacity
        self._store: list = []

    def add(self, record: dict) -> None:
        self._store.append(record)
        if len(self._store) > self.capacity:
            self._store = self._store[-self.capacity:]

    def recent(self) -> list:
        return list(self._store)

    def clear(self) -> None:
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)
