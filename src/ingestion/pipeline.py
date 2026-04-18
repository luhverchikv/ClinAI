from typing import List
import logging
from .file_loader import FileLoader
from .yaml_parser import YAMLParser, YAMLParseError
from .validator import DataValidator
from .json_collector import JSONCollector
from .models import ParsedProtocol, ValidationResult
from ..utils.config import load_config
logger = logging.getLogger(__name__)

def run_ingestion_pipeline(config_path: str = "config/validation_rules.yaml", source_dir: str = "clinical_protocols") -> dict:
    config = load_config(config_path)
    loader, parser, validator, collector = FileLoader(source_dir), YAMLParser(), DataValidator(config), JSONCollector()
    results, parsed = [], []
    for fp in loader.list_files():
        try:
            fname, content = loader.read_file(fp)
            meta, body = parser.extract_frontmatter(content)
            sections = parser.parse_sections(body)
            val = validator.validate_metadata(meta or {}, fname)
            missing = validator.validate_sections(sections, fname)
            if missing: val.warnings.append(f"Missing sections: {missing}")
            results.append(val)
            if val.is_valid:
                from .models import ProtocolMetadata
                parsed.append(ParsedProtocol(source_file=fname, metadata=ProtocolMetadata(**(meta or {})), sections=sections, raw_content=content))
        except YAMLParseError as e: logger.error(f"{fname}: {e}"); results.append(ValidationResult(file_path=str(fp), is_valid=False, errors=[str(e)]))
        except Exception as e: logger.exception(f"{fname}: {e}"); results.append(ValidationResult(file_path=str(fp), is_valid=False, errors=[str(e)]))
    results = validator.validate_uniqueness(results)
    summary = validator.get_summary(results)
    return {"summary": summary, "validation_report": collector.collect_validation_report(results, summary),
            "protocols_json": collector.collect_protocols(parsed), "by_icd10": collector.collect_by_icd10(parsed),
            "parsed_count": len(parsed), "valid_count": summary["valid_files"]}