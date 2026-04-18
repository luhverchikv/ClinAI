from typing import List, Dict, Any
import logging, re
from .models import ValidationResult
logger = logging.getLogger(__name__)

class DataValidator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.required_fields = config.get("required_fields", [])
        self.rules = config.get("validation_rules", {})
        self.required_sections = config.get("required_sections", [])
    def validate_metadata(self, metadata: dict, filename: str) -> ValidationResult:
        res = ValidationResult(file_path=filename, is_valid=True, extracted_fields=metadata.copy())
        for f in self.required_fields:
            if not metadata.get(f): res.errors.append(f"Missing required: {f}"); res.missing_required.append(f); res.is_valid = False
        for field, rules in self.rules.items():
            val = metadata.get(field)
            if not val: continue
            if "pattern" in rules and not re.match(rules["pattern"], str(val)): res.errors.append(f"Pattern mismatch: {field}"); res.is_valid = False
            if "allowed_values" in rules and val not in rules["allowed_values"]: res.errors.append(f"Invalid value: {field}={val}"); res.is_valid = False
        if metadata.get("id") and metadata.get("icd10_code") and metadata["id"] != metadata["icd10_code"]: res.warnings.append("id != icd10_code")
        return res
    def validate_sections(self, sections: dict, filename: str) -> List[str]:
        missing = [req for req in self.required_sections if not any(req in name for name in sections.keys())]
        if missing: logger.warning(f"{filename}: Missing sections: {missing}")
        return missing
    def validate_uniqueness(self, results: List[ValidationResult]) -> List[ValidationResult]:
        seen = {}
        for r in results:
            code = r.extracted_fields.get("icd10_code")
            if not code: continue
            if code in seen: r.errors.append(f"Duplicate icd10: {code} (also in {seen[code]})"); r.is_valid = False
            else: seen[code] = r.file_path
        return results
    def get_summary(self, results: List[ValidationResult]) -> dict:
        total = len(results); valid = sum(1 for r in results if r.is_valid)
        return {"total_files": total, "valid_files": valid, "invalid_files": total-valid,
                "total_errors": sum(len(r.errors) for r in results),
                "success_rate": f"{valid/total*100:.1f}%" if total else "0%"}