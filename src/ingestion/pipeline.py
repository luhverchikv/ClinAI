# src/ingestion/pipeline.py
from pathlib import Path
from typing import List
import logging
from .file_loader import FileLoader
from .yaml_parser import YAMLParser, YAMLParseError
from .validator import DataValidator
from .json_collector import JSONCollector
from .models import ParsedProtocol, ValidationResult
from ..utils.config import load_config

logger = logging.getLogger(__name__)

def run_ingestion_pipeline(config_path: str = "config/validation_rules.yaml",
                          source_dir: str = "clinical_protocols") -> dict:
    """
    Запускает полный пайплайн: загрузка → парсинг → валидация → JSON
    Возвращает сводку результатов
    """
    # Загрузка конфигурации
    config = load_config(config_path)
    
    # Инициализация компонентов
    loader = FileLoader(source_dir)
    parser = YAMLParser()
    validator = DataValidator(config)
    collector = JSONCollector()
    
    results: List[ValidationResult] = []
    parsed_protocols: List[ParsedProtocol] = []
    
    # Обработка каждого файла
    for file_path in loader.list_files():
        try:
            filename, content = loader.read_file(file_path)
            logger.info(f"Обработка: {filename}")
            
            # Парсинг
            metadata, body = parser.extract_frontmatter(content)
            sections = parser.parse_sections(body)
            
            # Валидация метаданных
            validation = validator.validate_metadata(metadata or {}, filename)
            
            # Валидация секций
            missing_sections = validator.validate_sections(sections, filename)
            if missing_sections:
                validation.warnings.append(f"Отсутствуют секции: {missing_sections}")
            
            results.append(validation)
            
            # Если валидация прошла (или только предупреждения) — собираем протокол
            if validation.is_valid or not config.get('report', {}).get('fail_on_critical'):
                from ..ingestion.models import ProtocolMetadata
                meta_model = ProtocolMetadata(**(metadata or {}))
                protocol = ParsedProtocol(
                    source_file=filename,
                    metadata=meta_model,
                    sections=sections,
                    raw_content=content
                )
                parsed_protocols.append(protocol)
                
        except YAMLParseError as e:
            logger.error(f"{filename}: Ошибка парсинга YAML: {e}")
            results.append(ValidationResult(
                file_path=str(file_path),
                is_valid=False,
                errors=[f"YAML parse error: {str(e)}"]
            ))
        except Exception as e:
            logger.exception(f"{filename}: Неожиданная ошибка: {e}")
            results.append(ValidationResult(
                file_path=str(file_path),
                is_valid=False,
                errors=[f"Unexpected error: {str(e)}"]
            ))
    
    # Пост-валидация уникальности
    results = validator.validate_uniqueness(results)
    
    # Генерация отчётов
    summary = validator.get_summary(results)
    report_path = collector.collect_validation_report(results, summary)
    protocols_path = collector.collect_protocols(parsed_protocols)
    by_icd10_paths = collector.collect_by_icd10(parsed_protocols)
    
    # Логирование итогов
    logger.info(f"✅ Валидация завершена: {summary['success_rate']} успешно")
    if summary['total_errors'] > 0:
        logger.warning(f"⚠️ Найдено ошибок: {summary['total_errors']}")
    
    return {
        "summary": summary,
        "validation_report": report_path,
        "protocols_json": protocols_path,
        "by_icd10": by_icd10_paths,
        "parsed_count": len(parsed_protocols),
        "valid_count": summary['valid_files']
    }

