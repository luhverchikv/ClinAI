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
    """
    Иерархический чанкер для медицинских протоколов.
    
    Стратегия:
    1. Разбиваем по секциям ## (основные блоки)
    2. Внутри секций — по подразделам ### (если есть)
    3. Если блок > max_chars — делим по абзацам с overlap
    4. Обогащаем метаданными
    """
    
    def __init__(
        self,
        min_chunk_chars: int = 100,
        max_chunk_chars: int = 800,
        overlap_chars: int = 50,
        preserve_medical_formatting: bool = True
    ):
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars
        self.normalizer = TextNormalizer(
            keep_emojis=False, 
            normalize_dosages=True
        )
    
    def chunk_protocol(
        self,
        source_file: str,
        icd10_code: str,
        diagnosis: str,
        sections: dict[str, str],
        tags: Optional[List[str]] = None
    ) -> Iterator[ProtocolChunk]:
        """
        Генерирует чанки для одного протокола.
        
        Yields:
            ProtocolChunk — готовый к векторизации чанк
        """
        chunk_index = 0
        
        # Парсим секции в иерархические блоки
        for section_title, section_content in sections.items():
            blocks = SectionParser.parse(section_content)
            
            # Если подразделов нет — обрабатываем всю секцию как один блок
            if not blocks:
                blocks = [SectionBlock(
                    title=section_title,
                    level=2,
                    content=section_content,
                    hierarchy_path=section_title
                )]
            
            for block in blocks:
                # Нормализуем контент
                clean_content = self.normalizer.normalize(
                    block.content, 
                    preserve_structure=False
                )
                
                if len(clean_content) < self.min_chunk_chars:
                    continue  # Пропускаем слишком короткие блоки
                
                # Разбиваем на чанки с overlap если нужно
                for subchunk in self._split_with_overlap(clean_content):
                    # Извлекаем сущности
                    meds = MedicationExtractor.extract(subchunk)
                    keywords = MedicationExtractor.extract_keywords(subchunk)
                    
                    # Генерируем чанк
                    chunk = ProtocolChunk(
                        chunk_id=ProtocolChunk.generate_id(
                            icd10_code, 
                            block.get_section_type(), 
                            subchunk, 
                            chunk_index
                        ),
                        source_file=source_file,
                        icd10_code=icd10_code,
                        diagnosis=diagnosis,
                        section_type=block.get_section_type()
                         if section_type == "other":
                             section_type = self._map_section_title(section_title)
                         subsection=block.title if block.level == 3 else None,
                        hierarchy_path=block.hierarchy_path,
                        content=subchunk,
                        content_type=self._detect_content_type(subchunk),
                        medications=[m.model_dump() for m in meds],
                        keywords=keywords,
                        tags=tags or [],
                        char_count=len(subchunk),
                        token_estimate=len(subchunk) // 4  # Грубая оценка для рус. текста
                    )
                    
                    yield chunk
                    chunk_index += 1
    
    def _split_with_overlap(self, text: str) -> List[str]:
        """Разбивает текст на чанки с перекрытием"""
        if len(text) <= self.max_chunk_chars:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Ищем ближайшую границу предложения или абзаца
            end = min(start + self.max_chunk_chars, len(text))
            
            # Если не конец текста — ищем удобную точку разрыва
            if end < len(text):
                # Приоритет: абзац > точка с пробелом > запятая
                for sep in ['\n\n', '. ', ', ']:
                    pos = text.rfind(sep, start + self.min_chunk_chars, end)
                    if pos != -1:
                        end = pos + len(sep)
                        break
            
            chunk = text[start:end].strip()
            if len(chunk) >= self.min_chunk_chars:
                chunks.append(chunk)
            
            # Сдвигаем с overlap
            start = end - self.overlap_chars if end < len(text) else len(text)
        
        return chunks
    
    def _detect_content_type(self, text: str) -> str:
        """Определяет тип контента для оптимизации эмбеддинга"""
        if re.match(r'^[\-\*\+]\s+', text, re.MULTILINE):
            return "list"
        if '|' in text and re.search(r'\|.*\|', text):
            return "table"
        if re.search(r'\d+\.\s+|^[→•▪]\s+', text, re.MULTILINE):
            return "algorithm"
        return "text"
        
    
    def _map_section_title(self, title: str) -> str:
        """Маппинг заголовка ## на тип секции"""
        t = title.lower()
        if "общая информация" in t: return "general"
        if "диагност" in t: return "diagnostics"
        if "лечение" in t: 
            if any(x in t for x in ["купир", "неотлож", "остр"]): return "treatment_acute"
            return "treatment"
        if "наблюд" in t: return "monitoring"
        if "противопоказ" in t: return "contraindications"
        return "other"

