from __future__ import annotations

from abc import ABC, abstractmethod

from aegis.logging_.event_log import StructuredLogger
from aegis.tools.base import ToolResult


class Skill(ABC):
    name: str

    @abstractmethod
    def run(self, user_message: str, request_id: str, logger: StructuredLogger) -> ToolResult: ...
