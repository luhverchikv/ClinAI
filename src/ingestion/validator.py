# src/ingestion/validator.py
from typing import List, Dict, Any
import logging
import re
from .models import ProtocolMetadata, ValidationResult

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Валидирует распарсенные данные клинических протоколов.
    Проверяет: наличие полей, форматы, бизнес-правила, секции.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.required_fields = config.get('required_fields', [])
        self.optional_fields = config.get('optional_fields', [])
        self.rules = config.get('validation_rules', {})
        self.required_sections = config.get('required_sections', [])
    
    def validate_metadata(self, meta dict, filename: str) -> ValidationResult:
        """Полная валидация метаданных одного файла"""
        result = ValidationResult(
            file_path=filename,
            is_valid=True,
            extracted_fields=metadata.copy()
        )
        
        # 1. Проверка обязательных полей
        for field in self.required_fields:
            if field not in metadata or not metadata[field]:
                result.errors.append(f"Отсутствует обязательное поле: {field}")
                result.missing_required.append(field)
                result.is_valid = False
        
        # 2. Проверка форматов по правилам
        for field, rules in self.rules.items():
            if field not in metadata or not metadata[field]:
                continue  # Пропускаем, если поле пустое (проверено выше)
            
            value = metadata[field]
            
            # Pattern validation
            if 'pattern' in rules:
                if not re.match(rules['pattern'], str(value)):
                    result.errors.append(
                        f"Поле '{field}' не соответствует паттерну: {value}"
                    )
                    result.is_valid = False
            
            # Allowed values
            if 'allowed_values' in rules:
                if value not in rules['allowed_values']:
                    result.errors.append(
                        f"Поле '{field}' имеет недопустимое значение: {value}. "
                        f"Допустимы: {rules['allowed_values']}"
                    )
                    result.is_valid = False
            
            # List type validation
            if rules.get('type') == 'list' and not isinstance(value, list):
                result.errors.append(f"Поле '{field}' должно быть списком")
                result.is_valid = False
        
        # 3. Проверка соответствия id и icd10_code
        if (self.rules.get('id', {}).get('must_match_icd10') and 
            metadata.get('id') and metadata.get('icd10_code')):
            if metadata['id'] != metadata['icd10_code']:
                result.warnings.append(
                    f"Поле 'id' ({metadata['id']}) не совпадает с 'icd10_code' "
                    f"({metadata['icd10_code']})"
                )
        
        # 4. Проверка уникальности (будет заполняться внешним трекером)
        # См. метод validate_uniqueness ниже
        
        return result
    
    def validate_sections(self, sections: Dict[str, str], filename: str) -> List[str]:
        """Проверяет наличие обязательных секций в Markdown"""
        missing = []
        section_names = list(sections.keys())
        
        for required in self.required_sections:
            # Ищем точное совпадение или частичное (для устойчивости к эмодзи)
            if not any(required in name for name in section_names):
                missing.append(required)
        
        if missing:
            logger.warning(f"{filename}: Отсутствуют секции: {missing}")
        
        return missing
    
    def validate_uniqueness(self, results: List[ValidationResult]) -> List[ValidationResult]:
        """
        Пост-валидация: проверяет уникальность полей (icd10_code, id)
        Вызывается после валидации всех файлов
        """
        seen_codes = {}
        
        for result in results:
            icd10 = result.extracted_fields.get('icd10_code')
            if not icd10:
                continue
            
            if icd10 in seen_codes:
                result.errors.append(
                    f"Дубликат icd10_code '{icd10}'. Уже есть в: {seen_codes[icd10]}"
                )
                result.is_valid = False
            else:
                seen_codes[icd10] = result.file_path
        
        return results
    
    def get_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Генерирует сводный отчёт по валидации"""
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        errors = sum(len(r.errors) for r in results)
        warnings = sum(len(r.warnings) for r in results)
        
        return {
            "total_files": total,
            "valid_files": valid,
            "invalid_files": total - valid,
            "total_errors": errors,
            "total_warnings": warnings,
            "success_rate": f"{valid/total*100:.1f}%" if total > 0 else "N/A",
            "files_with_errors": [
                {"file": r.file_path, "errors": r.errors} 
                for r in results if r.errors
            ]
        }

