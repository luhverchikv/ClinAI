from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
import re

class ProtocolMetadata(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    id: str = Field(..., min_length=1)
    diagnosis: str = Field(..., min_length=1)
    icd10_code: str = Field(...)
    protocol_name: str = Field(..., min_length=1)
    protocol_number: Optional[str] = None
    publish_date: Optional[str] = None
    official_url: Optional[str] = None
    status: str = Field(..., pattern="^(active|archived|draft)$")
    tags: Optional[List[str]] = Field(default_factory=list)
    verification_status: Optional[str] = "unverified"
    @field_validator("icd10_code")
    @classmethod
    def validate_icd10(cls, v): return re.sub(r"^[A-Z]\d{2}", lambda m: m.group(0).upper(), v)

class ParsedProtocol(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    source_file: str
    metadata: ProtocolMetadata
    sections: dict[str, str]
    raw_content: str
    parsed_at: datetime = Field(default_factory=datetime.now)

class ValidationResult(BaseModel):
    file_path: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    extracted_fields: dict = Field(default_factory=dict)
    missing_required: List[str] = Field(default_factory=list)