# src/chunking/pipeline.py
import json
from pathlib import Path
from typing import Iterator, List
from src.ingestion.models import ParsedProtocol
from src.chunking.hierarchical_chunker import HierarchicalChunker
from src.models.chunk import ProtocolChunk
import logging

logger = logging.getLogger(__name__)

class ChunkingPipeline:
    """Оркестрирует процесс чанкинга для всех протоколов"""
    
    def __init__(self, output_dir: str = "data/chunks", **chunker_kwargs):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunker = HierarchicalChunker(**chunker_kwargs)
    
    def process_protocols(self, protocols_path: str) -> dict:
        """
        Загружает распарсенные протоколы и генерирует чанки.
        
        Returns:
            dict со статистикой и путями к выходным файлам
        """
        # Загружаем данные из Шага 1
        with open(protocols_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_chunks: List[ProtocolChunk] = []
        stats = {
            "total_protocols": 0,
            "total_chunks": 0,
            "chunks_by_section": {},
            "chunks_with_medications": 0
        }
        
        for protocol_data in data.get("protocols", []):
            stats["total_protocols"] += 1
            
            # Создаём чанки
            chunks = list(self.chunker.chunk_protocol(
                source_file=protocol_data["source_file"],
                icd10_code=protocol_data["metadata"]["icd10_code"],
                diagnosis=protocol_data["metadata"]["diagnosis"],
                sections=protocol_data["sections"],
                tags=protocol_data["metadata"].get("tags", [])
            ))
            
            # Обновляем статистику
            for chunk in chunks:
                all_chunks.append(chunk)
                sec_type = chunk.section_type
                stats["chunks_by_section"][sec_type] = stats["chunks_by_section"].get(sec_type, 0) + 1
                if chunk.medications:
                    stats["chunks_with_medications"] += 1
            
            stats["total_chunks"] += len(chunks)
            logger.info(f"{protocol_data['metadata']['icd10_code']}: {len(chunks)} чанков")
        
        # Сохраняем результаты
        return self._save_chunks(all_chunks, stats)
    
    def _save_chunks(self, chunks: List[ProtocolChunk], stats: dict) -> dict:
        """Сохраняет чанки в разных форматах"""
        results = {}
        
        # 1. Единый JSON со всеми чанками
        all_path = self.output_dir / "all_chunks.json"
        with open(all_path, 'w', encoding='utf-8') as f:
            json.dump({
                "generated_at": stats.get("generated_at"),
                "total_chunks": len(chunks),
                "chunks": [c.to_vector_record() for c in chunks]
            }, f, ensure_ascii=False, indent=2)
        results["all_chunks"] = str(all_path)
        
        # 2. По кодам МКБ-10 (для инкрементального обновления)
        by_icd10_dir = self.output_dir / "by_icd10"
        by_icd10_dir.mkdir(exist_ok=True)
        
        chunks_by_code = {}
        for chunk in chunks:
            if chunk.icd10_code not in chunks_by_code:
                chunks_by_code[chunk.icd10_code] = []
            chunks_by_code[chunk.icd10_code].append(chunk)
        
        for icd10, code_chunks in chunks_by_code.items():
            fp = by_icd10_dir / f"{icd10}_chunks.json"
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump({
                    "icd10_code": icd10,
                    "chunk_count": len(code_chunks),
                    "chunks": [c.to_vector_record() for c in code_chunks]
                }, f, ensure_ascii=False, indent=2)
        
        results["by_icd10_dir"] = str(by_icd10_dir)
        results["stats"] = stats
        
        logger.info(f"✅ Создано {len(chunks)} чанков из {stats['total_protocols']} протоколов")
        return results

