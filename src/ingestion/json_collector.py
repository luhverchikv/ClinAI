import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from .models import ParsedProtocol, ValidationResult
import logging
logger = logging.getLogger(__name__)

class JSONCollector:
    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = Path(output_dir); self.output_dir.mkdir(parents=True, exist_ok=True)
    def collect_protocols(self, parsed: List[ParsedProtocol]) -> str:
        out = self.output_dir / "protocols.json"
        with open(out, "w", encoding="utf-8") as f: json.dump({"exported_at": datetime.now().isoformat(), "count": len(parsed), "protocols": [p.model_dump(mode="json") for p in parsed]}, f, ensure_ascii=False, indent=2)
        return str(out)
    def collect_validation_report(self, results: List[ValidationResult], summary: dict) -> str:
        out = self.output_dir / "validation_report.json"
        with open(out, "w", encoding="utf-8") as f: json.dump({"generated_at": datetime.now().isoformat(), "summary": summary, "details": [r.model_dump() for r in results]}, f, ensure_ascii=False, indent=2)
        return str(out)
    def collect_by_icd10(self, parsed: List[ParsedProtocol]) -> Dict[str, str]:
        out_dir = self.output_dir / "by_icd10"; out_dir.mkdir(exist_ok=True)
        paths = {}
        for p in parsed:
            fp = out_dir / f"{p.metadata.icd10_code}.json"
            with open(fp, "w", encoding="utf-8") as f: json.dump(p.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
            paths[p.metadata.icd10_code] = str(fp)
        return paths