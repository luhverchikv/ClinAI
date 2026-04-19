# src/chunking/simple_chunker.py
import re
from typing import Iterator, Optional
from src.models.chunk import SimpleChunk

class SimpleChunker:
    """
    Простой чанкер: разбивает Markdown по заголовкам ## и ###.
    Один подраздел (###) = один чанк (если не слишком длинный).
    """
    
    # Маппинг заголовков ## на типы секций
    SECTION_MAP = {
        "общая информация": "general",
        "описание": "general",
        "диагност": "diagnostics",
        "обследован": "diagnostics",
        "лечение": "treatment",
        "терап": "treatment",
        "купир": "treatment_acute",  # подраздел лечения
        "неотлож": "treatment_acute",
        "остр": "treatment_acute",
        "профилакт": "treatment",
        "поддерж": "treatment",
        "наблюд": "monitoring",
        "монитор": "monitoring",
        "противопоказ": "contraindications",
        "осложн": "side_effects",
    }
    
    MAX_CHUNK_CHARS = 1000  # Если подраздел длиннее — разобьём по абзацам
    
    @classmethod
    def _map_section_type(cls, title: str) -> str:
        """Определяет тип секции по заголовку"""
        t = title.lower()
        for key, val in cls.SECTION_MAP.items():
            if key in t:
                return val
        return "other"
    
    @classmethod
    def chunk_protocol(
        cls,
        source_file: str,
        icd10_code: str,
        diagnosis: str,
        sections: dict[str, str],
        tags: Optional[list[str]] = None
    ) -> Iterator[SimpleChunk]:
        """Генерирует чанки из одного протокола"""
        
        for section_title, section_content in sections.items():
            section_type = cls._map_section_type(section_title)
            
            # Парсим подразделы ### внутри секции
            subsections = cls._parse_subsections(section_content)
            
            # Если подразделов нет — вся секция = один чанк
            if not subsections:
                yield cls._make_chunk(
                    icd10_code, diagnosis, section_type, 
                    section_title, section_content, tags
                )
                continue
            
            # Иначе — по одному чанку на подраздел
            for sub_title, sub_content in subsections:
                # Если подраздел слишком длинный — делим по абзацам
                if len(sub_content) > cls.MAX_CHUNK_CHARS:
                    for i, part in enumerate(cls._split_by_paragraphs(sub_content)):
                        yield cls._make_chunk(
                            icd10_code, diagnosis, section_type,
                            f"{section_title} > {sub_title} [{i+1}]", part, tags
                        )
                else:
                    yield cls._make_chunk(
                        icd10_code, diagnosis, section_type,
                        sub_title, sub_content, tags
                    )
    
    @staticmethod
    def _parse_subsections(content: str) -> list[tuple[str, str]]:
        """Извлекает подразделы ### из контента секции"""
        subsections = []
        pattern = re.compile(r'^###\s+(.+?)\n(.*?)(?=\n###\s+|$)', re.MULTILINE | re.DOTALL)
        for match in pattern.finditer(content.strip()):
            title = match.group(1).strip()
            body = match.group(2).strip()
            if body:  # Пропускаем пустые
                subsections.append((title, body))
        return subsections
    
    @staticmethod
    def _split_by_paragraphs(text: str, max_len: int = 800) -> list[str]:
        """Делит длинный текст по абзацам с сохранением смысла"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs:
            return [text]
        
        chunks, current = [], []
        current_len = 0
        
        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > max_len and current:
                chunks.append('\n\n'.join(current))
                current, current_len = [para], para_len
            else:
                current.append(para)
                current_len += para_len + 2
        
        if current:
            chunks.append('\n\n'.join(current))
        
        return chunks if chunks else [text]
    
    @classmethod
    def _make_chunk(
        cls,
        icd10_code: str,
        diagnosis: str,
        section_type: str,
        subsection: str,
        content: str,
        tags: Optional[list[str]]
    ) -> SimpleChunk:
        """Создаёт объект чанка"""
        # Очищаем контент: убираем лишние пробелы, но сохраняем структуру
        clean_content = re.sub(r'\n{3,}', '\n\n', content.strip())
        
        return SimpleChunk(
            chunk_id=SimpleChunk.generate_id(icd10_code, section_type, subsection, clean_content),
            icd10_code=icd10_code,
            diagnosis=diagnosis,
            section_type=section_type,
            subsection=subsection,
            content=clean_content,
            tags=tags or []
        )

