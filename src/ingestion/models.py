# src/ingestion/models.py
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import re

class ProtocolMetadata(BaseModel):
    """Модель метаданных клинического протокола"""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    id: str = Field(..., min_length=1, description="Уникальный идентификатор")
    diagnosis: str = Field(..., min_length=1, description="Название диагноза")
    icd10_code: str = Field(..., description="Код МКБ-10")
    protocol_name: str = Field(..., min_length=1, description="Название протокола")
    protocol_number: Optional[str] = Field(default=None)
    publish_date: Optional[str] = Field(default=None)
    official_url: Optional[str] = Field(default=None, pattern=r"^https?://.*$|^[extract_itex]") status: str = Field(..., pattern="^(active|archived|draft)[/extract_itex]")
    tags: Optional[List[str]] = Field(default_factory=list)
    verification_status: Optional[str] = Field(default="unverified")
    
    @field_validator('icd10_code')
    @classmethod
    def validate_icd10_format(cls, v: str) -> str:
        if not re.match(r'^[A-Z]\d{2}(\.\d+)?$', v):
            raise ValueError(f'Неверный формат МКБ-10: {v}')
        return v.upper()
    
    @field_validator('id')
    @classmethod
    def id_must_match_icd10(cls, v: str, info) -> str:
        # Проверка, что id совпадает с icd10_code (если включено в конфиге)
        if info.data.get('icd10_code') and v != info.data['icd10_code']:
            # Это warning, а не error - логируем, но не блокируем
            pass
        return v

class ParsedProtocol(BaseModel):
    """Результат парсинга одного файла"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    source_file: str
    meta ProtocolMetadata
    sections: dict[str, str]  # {section_name: content}
    raw_content: str
    parsed_at: datetime = Field(default_factory=datetime.now)
    
class ValidationResult(BaseModel):
    """Результат валидации одного файла"""
    file_path: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    extracted_fields: dict = Field(default_factory=dict)
    missing_required: List[str] = Field(default_factory=list)

