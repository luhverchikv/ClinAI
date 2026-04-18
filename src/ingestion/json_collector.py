# src/ingestion/json_collector.py
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from .models import ParsedProtocol, ValidationResult
import logging

logger = logging.getLogger(__name__)

class JSONCollector:
    """Собирает валидированные данные в структурированный JSON"""
    
    def __init__(self, output_dir: str = "data/processed"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def collect_protocols(self, parsed: List[ParsedProtocol]) -> str:
        """Сохраняет все протоколы в единый JSON-файл"""
        output_path = self.output_dir / "protocols.json"
        
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_protocols": len(parsed),
            "protocols": [p.model_dump(mode='json') for p in parsed]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Сохранено {len(parsed)} протоколов в {output_path}")
        return str(output_path)
    
    def collect_validation_report(self, results: List[ValidationResult], 
                                  summary: Dict[str, Any]) -> str:
        """Сохраняет отчёт валидации"""
        output_path = self.output_dir / "validation_report.json"
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary,
            "detailed_results": [r.model_dump() for r in results]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Отчёт валидации сохранён в {output_path}")
        return str(output_path)
    
    def collect_by_icd10(self, parsed: List[ParsedProtocol]) -> Dict[str, str]:
        """
        Создаёт отдельные JSON-файлы по кодам МКБ-10
        Возвращает: {icd10_code: file_path}
        """
        output_paths = {}
        
        for protocol in parsed:
            icd10 = protocol.metadata.icd10_code
            filename = f"{icd10}.json"
            output_path = self.output_dir / "by_icd10" / filename
            output_path.parent.mkdir(exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(protocol.model_dump(mode='json'), f, 
                         ensure_ascii=False, indent=2)
            
            output_paths[icd10] = str(output_path)
        
        logger.info(f"Создано {len(output_paths)} файлов по МКБ-10")
        return output_paths

