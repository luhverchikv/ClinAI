# -*- coding: utf-8 -*-
"""
Базовый класс для экстракторов клинических протоколов.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ClinicalChunk:
    """Фрагмент клинического протокола для векторной БД."""
    chunk_id: str
    diagnosis: str
    icd_code: str
    section_type: str  # diagnosis | treatment | prophylaxis | emergency
    title: str
    content: str
    medications: List[Dict[str, Any]] = field(default_factory=list)
    procedures: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    indications: List[str] = field(default_factory=list)
    monitoring: List[str] = field(default_factory=list)
    source_file: str = ""
    source_page: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для JSON."""
        return {
            "chunk_id": self.chunk_id,
            "diagnosis": self.diagnosis,
            "icd_code": self.icd_code,
            "section_type": self.section_type,
            "title": self.title,
            "content": self.content,
            "medications": self.medications,
            "procedures": self.procedures,
            "contraindications": self.contraindications,
            "indications": self.indications,
            "monitoring": self.monitoring,
            "source_file": self.source_file,
            "source_page": self.source_page
        }


class BaseExtractor(ABC):
    """Базовый класс экстрактора."""

    @abstractmethod
    def extract(self, file_path: str) -> List[ClinicalChunk]:
        """Извлечение фрагментов из файла."""
        pass

    @abstractmethod
    def extract_from_text(self, text: str, source_file: str = "") -> List[ClinicalChunk]:
        """Извлечение фрагментов из текста."""
        pass
