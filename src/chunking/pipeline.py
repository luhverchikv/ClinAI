# src/chunking/pipeline.py
import json
from pathlib import Path
from typing import List
from src.chunking.simple_chunker import SimpleChunker
from src.models.chunk import SimpleChunk
import logging

logger = logging.getLogger(__name__)

class SimpleChunkingPipeline:
    """Оркестрация простого чанкинга"""
    
    def __init__(self, output_dir: str = "data/chunks"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def process_protocols(self, protocols_path: str) -> dict:
        """Загружает протоколы и генерирует чанки"""
        with open(protocols_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks: List[SimpleChunk] = []
        stats = {"total_protocols": 0, "total_chunks": 0, "by_section": {}}
        
        for proto in data.get("protocols", []):
            stats["total_protocols"] += 1
            meta = proto["metadata"]
            
            for chunk in SimpleChunker.chunk_protocol(
                source_file=proto["source_file"],
                icd10_code=meta["icd10_code"],
                diagnosis=meta["diagnosis"],
                sections=proto["sections"],
                tags=meta.get("tags", [])
            ):
                chunks.append(chunk)
                sec = chunk.section_type
                stats["by_section"][sec] = stats["by_section"].get(sec, 0) + 1
            
            stats["total_chunks"] += 1
            logger.info(f"{meta['icd10_code']}: +{len([c for c in chunks if c.icd10_code == meta['icd10_code']])} чанков")
        
        return self._save(chunks, stats)
    
    def _save(self, chunks: List[SimpleChunk], stats: dict) -> dict:
        """Сохраняет чанки в JSON"""
        # Все чанки в одном файле
        all_path = self.output_dir / "all_chunks.json"
        with open(all_path, 'w', encoding='utf-8') as f:
            json.dump({
                "total": len(chunks),
                "chunks": [c.to_vector_record() for c in chunks]
            }, f, ensure_ascii=False, indent=2)
        
        # По МКБ-10 для инкрементальных обновлений
        by_code_dir = self.output_dir / "by_icd10"
        by_code_dir.mkdir(exist_ok=True)
        
        from collections import defaultdict
        grouped = defaultdict(list)
        for c in chunks:
            grouped[c.icd10_code].append(c)
        
        for code, code_chunks in grouped.items():
            fp = by_code_dir / f"{code}.json"
            with open(fp, 'w', encoding='utf-8') as f:
                json.dump({
                    "icd10_code": code,
                    "count": len(code_chunks),
                    "chunks": [c.to_vector_record() for c in code_chunks]
                }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Сохранено {len(chunks)} чанков")
        return {"all_chunks": str(all_path), "by_icd10": str(by_code_dir), "stats": stats}

