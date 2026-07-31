"""LLM'in sectigi (ya da otomatik cozulen) literal aday string'ini gercek
sandbox dosya sistemi path'ine cevirir. LLM ciktisi ile gercek dosya sistemi
arasindaki tek I/O'lu koprudur - bu katman disinda hicbir yerde LLM ciktisi
dogrudan dosya sistemi islemi icin kullanilmaz."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum

from aegis.extraction.candidates import normalize

YOK = "YOK"


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"
    NOT_NEEDED = "NOT_NEEDED"  # aday YOK ise


@dataclass
class Resolution:
    status: ResolutionStatus
    resolved_path: str | None = None
    matches: list[str] = field(default_factory=list)


class PathResolver:
    def __init__(self, sandbox_root: str, max_depth: int = 3):
        self.sandbox_root = os.path.abspath(sandbox_root)
        self.max_depth = max_depth

    def _walk_entries(self) -> list[str]:
        entries: list[str] = []
        root_depth = self.sandbox_root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(self.sandbox_root):
            depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
            if depth >= self.max_depth:
                dirnames[:] = []
                continue
            for name in dirnames + filenames:
                entries.append(os.path.join(dirpath, name))
        return entries

    def resolve(self, candidate: str) -> Resolution:
        if candidate == YOK:
            return Resolution(status=ResolutionStatus.NOT_NEEDED)

        entries = self._walk_entries()

        exact = [e for e in entries if os.path.basename(e) == candidate]
        if len(exact) == 1:
            return Resolution(status=ResolutionStatus.RESOLVED, resolved_path=exact[0])
        if len(exact) > 1:
            return Resolution(status=ResolutionStatus.AMBIGUOUS, matches=exact)

        candidate_lower = candidate.lower()
        case_insensitive = [e for e in entries if os.path.basename(e).lower() == candidate_lower]
        if len(case_insensitive) == 1:
            return Resolution(status=ResolutionStatus.RESOLVED, resolved_path=case_insensitive[0])
        if len(case_insensitive) > 1:
            return Resolution(status=ResolutionStatus.AMBIGUOUS, matches=case_insensitive)

        candidate_normalized = normalize(candidate)
        normalized_matches = [
            e for e in entries if normalize(os.path.basename(e)) == candidate_normalized
        ]
        if len(normalized_matches) == 1:
            return Resolution(status=ResolutionStatus.RESOLVED, resolved_path=normalized_matches[0])
        if len(normalized_matches) > 1:
            return Resolution(status=ResolutionStatus.AMBIGUOUS, matches=normalized_matches)

        substring_matches = [e for e in entries if candidate_lower in os.path.basename(e).lower()]
        if len(substring_matches) == 1:
            return Resolution(status=ResolutionStatus.RESOLVED, resolved_path=substring_matches[0])
        if len(substring_matches) > 1:
            return Resolution(status=ResolutionStatus.AMBIGUOUS, matches=substring_matches)

        return Resolution(status=ResolutionStatus.NOT_FOUND)
