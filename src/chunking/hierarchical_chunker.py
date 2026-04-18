# src/chunking/hierarchical_chunker.py
import re
from typing import List, Optional, Iterator
from src.models.chunk import ProtocolChunk, Medication
from src.preprocessing.text_normalizer import TextNormalizer
from src.preprocessing.section_parser import SectionParser, SectionBlock
from src.preprocessing.medication_extractor import MedicationExtractor
import logging

logger = logging.getLogger(__name__)

class HierarchicalChunker:
    def __init__(self, min_chunk_chars: int = 100, max_chunk_chars: int = 800,
                 overlap_chars: int = 50, preserve_medical_formatting: bool = True):
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars
        self.normalizer = TextNormalizer(keep_emojis=False, normalize_dosages=True)
    
    def _map_section_title(self, title: str) -> str:
        """Маппинг заголовка ## на тип секции"""
        t = title.lower()
        if "общая информация" in t: return "general"
        if "диагност" in t: return "diagnostics"
        if "лечение" in t:
            return "treatment_acute" if any(x in t for x in ["купир", "неотлож", "остр"]) else "treatment"
        if "наблюд" in t: return "monitoring"
        if "противопоказ" in t: return "contraindications"
        return "other"
    
    def chunk_protocol(self, source_file: str, icd10_code: str, diagnosis: str,
                      sections: dict[str, str], tags: Optional[List[str]] = None) -> Iterator[ProtocolChunk]:
        chunk_index = 0
        for section_title, section_content in sections.items():
            blocks = SectionParser.parse(section_content)
            if not blocks:
                blocks = [SectionBlock(title=section_title, level=2, content=section_content, hierarchy_path=section_title)]
            
            for block in blocks:
                clean_content = self.normalizer.normalize(block.content, preserve_structure=False)
                if len(clean_content) < self.min_chunk_chars:
                    continue
                for subchunk in self._split_with_overlap(clean_content):
                    meds = MedicationExtractor.extract(subchunk)
                    keywords = MedicationExtractor.extract_keywords(subchunk)
                    
                    # ✅ Правильная логика наследования типа
                    sec_type = block.get_section_type()
                    if sec_type == "other":
                        sec_type = self._map_section_title(section_title)
                    
                    chunk = ProtocolChunk(
                        chunk_id=ProtocolChunk.generate_id(icd10_code, sec_type, subchunk, chunk_index),
                        source_file=source_file, icd10_code=icd10_code, diagnosis=diagnosis,
                        section_type=sec_type,
                        subsection=block.title if block.level == 3 else None,
                        hierarchy_path=block.hierarchy_path, content=subchunk,
                        content_type=self._detect_content_type(subchunk),
                        medications=[m.model_dump(mode="json") for m in meds],
                        keywords=keywords, tags=tags or [],
                        char_count=len(subchunk), token_estimate=len(subchunk) // 4
                    )
                    yield chunk
                    chunk_index += 1
    
    def _split_with_overlap(self, text: str) -> List[str]:
        if len(text) <= self.max_chunk_chars:
            return [text]
        chunks, start = [], 0
        while start < len(text):
            end = min(start + self.max_chunk_chars, len(text))
            if end < len(text):
                for sep in ['\n\n', '. ', ', ']:
                    pos = text.rfind(sep, start + self.min_chunk_chars, end)
                    if pos != -1:
                        end = pos + len(sep)
                        break
            chunk = text[start:end].strip()
            if len(chunk) >= self.min_chunk_chars:
                chunks.append(chunk)
            start = end - self.overlap_chars if end < len(text) else len(text)
        return chunks
    
    def _detect_content_type(self, text: str) -> str:
        if re.match(r'^[\-\*\+]\s+', text, re.MULTILINE):
            return "list"
        if '|' in text and re.search(r'\|.*\|', text):
            return "table"
        if re.search(r'\d+\.\s+|^[→•▪]\s+', text, re.MULTILINE):
            return "algorithm"
        return "text"
