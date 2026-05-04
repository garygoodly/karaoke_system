from __future__ import annotations

from collections import deque


class RollingAverage:
    def __init__(self, size: int = 20) -> None:
        self.size = size
        self.values: deque[float] = deque(maxlen=size)

    def add(self, value: float) -> float:
        self.values.append(value)
        return self.value

    @property
    def value(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)
