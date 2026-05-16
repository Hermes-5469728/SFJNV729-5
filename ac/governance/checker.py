from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from typing import Any


@dataclass
class CheckResult:
    passed: bool
    level: str = "info"
    message: str = ""
    details: dict = field(default_factory=dict)


class BaseChecker(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def check(self, text: str, context: dict | None = None) -> CheckResult:
        ...


class CheckerRegistry:
    def __init__(self):
        self._checkers: list[BaseChecker] = []

    def register(self, checker: BaseChecker):
        self._checkers.append(checker)

    def all(self) -> list[BaseChecker]:
        return list(self._checkers)

    def by_name(self, name: str) -> BaseChecker | None:
        for c in self._checkers:
            if c.name == name:
                return c
        return None
