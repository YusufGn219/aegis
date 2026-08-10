"""Tool soyutlamasi: her tool kendi JSON semasini adaylardan dinamik olarak
insa eder (serbest string yerine enum) ve sadece zaten cozumlenmis, gercek
degerlerle calisir."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from aegis.extraction.candidates import Candidates

YOK = "YOK"


class RiskLevel(str, Enum):
    LOW = "LOW"  # salt-okunur, otomatik calisir (orn. list_files)
    MEDIUM = "MEDIUM"  # mutasyon var ama geri alinabilir/kontrollu (move/send) -> onay gerekir
    HIGH = "HIGH"  # yikici/geri alinamaz (delete_file, delete_event) -> onay + tam deger gosterimi


@dataclass
class ToolContext:
    sandbox_root: str
    candidates: Candidates


@dataclass
class ToolResult:
    success: bool
    message: str
    data: dict | None = None


@dataclass
class SlotRequirement:
    """Bir tool'un doldurulmasi gereken bir parametresi ve o parametre icin
    cikarilmis gercek aday listesi (invocation_policy bunu kullanir)."""

    slot_name: str
    candidates: list[str]
    is_filesystem_path: bool = False


class Tool(ABC):
    name: str
    description: str
    risk_level: RiskLevel

    @abstractmethod
    def build_schema(self, ctx: ToolContext) -> dict:
        """OpenAI-tarzi function/tool JSON semasi doner; metin alanlari
        icin serbest 'type: string' yerine ctx.candidates'tan turetilmis
        bir 'enum' listesi (+ YOK) kullanilir."""

    @abstractmethod
    def required_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        """invocation_policy.decide()'in kullandigi, bu tool icin zorunlu
        slotlarin ve onlara karsilik gelen aday listelerinin dokumu."""

    def optional_slots(self, ctx: ToolContext) -> list[SlotRequirement]:
        """Zorunlu olmayan ama skip_llm yolunda otomatik doldurulmasi
        istenen slotlar. Varsayilan bos liste - cogu tool'un opsiyonel
        alani yok. invocation_policy: 1 aday varsa otomatik doldurur,
        2+ aday varsa (gercek belirsizlik) LLM'e birakir - asla tahmin
        etmez; 0 aday varsa kullanici zaten hic bahsetmemis demektir."""
        return []

    @abstractmethod
    def execute(self, resolved_args: dict, ctx: ToolContext) -> ToolResult:
        """Sadece TAMAMEN cozumlenmis (path-resolve edilmis ya da literal
        icerik) degerlerle cagrilir - hic bir zaman ham LLM/aday string'i
        dosya sistemi alanlarina dogrudan gecmez."""
