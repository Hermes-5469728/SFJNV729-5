import sqlite3
import time
from pathlib import Path
from typing import Callable


class ACWatchdog:
    def __init__(self, data_dir: str = "data", poll_interval: float = 5.0):
        self.data_dir = Path(data_dir)
        self.poll_interval = poll_interval
        self.last_check: dict[str, str] = {}
        self.callbacks: list[Callable] = []

    def register_callback(self, cb: Callable) -> None:
        self.callbacks.append(cb)

    def scan(self) -> list[dict]:
        events = []
        if not self.data_dir.exists():
            return events
        for db_path in self.data_dir.glob("*.db"):
            product = db_path.stem
            last = self.last_check.get(product, "1970-01-01T00:00:00")
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT task_id, state, updated_at FROM status "
                    "WHERE updated_at > ? ORDER BY updated_at",
                    (last,),
                )
                for row in cursor.fetchall():
                    events.append({
                        "product": product,
                        "task_id": row[0],
                        "state": row[1],
                        "updated_at": row[2],
                        "db_path": str(db_path),
                    })
                    self.last_check[product] = max(
                        self.last_check.get(product, ""), row[2]
                    )
                conn.close()
            except sqlite3.OperationalError:
                continue
        return events

    def run_forever(self) -> None:
        while True:
            events = self.scan()
            for evt in events:
                for cb in self.callbacks:
                    cb(evt)
            time.sleep(self.poll_interval)
