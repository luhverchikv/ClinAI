# src/models/chunk.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib

class Medication(BaseModel):
    """Модель лекарственного препарата"""
    name: str
    dosage: Optional[str] = None
    route: Optional[str] = None  # способ введения: в/в, в/м, per os
    frequency: Optional[str] = None
    notes: Optional[str] = None

class ProtocolChunk(BaseModel):
    """Модель чанка для векторной базы данных"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Уникальный идентификатор (генерируется автоматически)
    chunk_id: str = Field(..., description="Уникальный ID чанка")
    
    # Ссылка на источник
    source_file: str
    icd10_code: str
    diagnosis: str
    
    # Тип и иерархия контента
    section_type: str  # "general", "diagnostics", "treatment_acute", "treatment_chronic", "monitoring", "contraindications"
    subsection: Optional[str] = None
    hierarchy_path: str  # "💊 Лечение > Купирование > Препараты"
    
    # Контент
    content: str = Field(..., min_length=10, description="Текст чанка для эмбеддинга")
    content_type: str = Field(default="text", pattern="^(text|list|table|algorithm)$")
    
    # Извлечённые сущности
    medications: List[Medication] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    
    # Метаданные для фильтрации
    tags: List[str] = Field(default_factory=list)
    risk_level: Optional[str] = Field(default=None, pattern="^(low|medium|high|critical)$")
    
    # Технические поля
    char_count: int
    token_estimate: int  # приблизительное количество токенов
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def generate_id(cls, icd10: str, section: str, content: str, index: int) -> str:
        """Генерирует детерминированный ID чанка"""
        hash_input = f"{icd10}:{section}:{content[:100]}:{index}"
        hash_val = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
        return f"{icd10}-{section}-{hash_val}"
    
    def to_vector_record(self) -> Dict[str, Any]:
        """Конвертирует чанк в формат для векторной БД"""
        return {
            "id": self.chunk_id,
            "vector_metadata": {
                "icd10_code": self.icd10_code,
                "diagnosis": self.diagnosis,
                "section_type": self.section_type,
                "tags": self.tags,
                "risk_level": self.risk_level
            },
            "payload": self.model_dump(mode="json")
        }

