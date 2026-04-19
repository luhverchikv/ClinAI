# src/models/chunk.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
import hashlib

class SimpleChunk(BaseModel):
    """Минималистичная модель чанка для векторной БД"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    chunk_id: str
    icd10_code: str
    diagnosis: str
    section_type: str  # general, diagnostics, treatment, monitoring, contraindications
    subsection: str | None  # например "Купирование приступа"
    content: str = Field(..., min_length=10)
    
    # Опциональные метаданные для фильтрации
    tags: list[str] = Field(default_factory=list)
    
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def generate_id(cls, icd10: str, section: str, subsection: str | None, content: str) -> str:
        """Детерминированный ID для идемпотентности"""
        key = f"{icd10}:{section}:{subsection or ''}:{content[:100]}"
        hash_val = hashlib.sha256(key.encode()).hexdigest()[:10]
        return f"{icd10}-{section}-{hash_val}"
    
    def to_vector_record(self) -> dict:
        """Формат для загрузки в векторную БД"""
        return {
            "id": self.chunk_id,
            "metadata": {
                "icd10_code": self.icd10_code,
                "diagnosis": self.diagnosis,
                "section_type": self.section_type,
                "subsection": self.subsection,
                "tags": self.tags
            },
            "text": self.content  # Поле для эмбеддинга
        }

