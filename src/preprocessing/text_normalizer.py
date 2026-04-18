# src/preprocessing/text_normalizer.py
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TextNormalizer:
    """Нормализует медицинский текст для чанкинга и эмбеддингов"""
    
    # Паттерны для очистки
    PATTERNS = {
        "extra_whitespace": re.compile(r'\s+'),
        "markdown_links": re.compile(r'\[([^\]]+)\]\([^)]+\)'),  # [текст](ссылка) → текст
        "markdown_bold": re.compile(r'\*\*([^*]+)\*\*'),  # **жирный** → жирный
        "markdown_italic": re.compile(r'\*([^*]+)\*'),  # *курсив* → курсив
        "dosage_range": re.compile(r'(\d+),(\d+)(?=\s*(?:мг|мл|г))'),  # 2,5 мг → 2.5 мг
        "emoji_cleanup": re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]'),  # опционально
    }
    
    def __init__(self, keep_emojis: bool = False, normalize_dosages: bool = True):
        self.keep_emojis = keep_emojis
        self.normalize_dosages = normalize_dosages
    
    def normalize(self, text: str, preserve_structure: bool = True) -> str:
        """
        Применяет цепочку нормализаций к тексту.
        
        Args:
            text: Исходный текст
            preserve_structure: Сохранять ли заголовки ## и ###
        """
        if not text or not isinstance(text, str):
            return ""
        
        result = text.strip()
        
        # 1. Нормализация пробелов и переносов
        result = self.PATTERNS["extra_whitespace"].sub(' ', result)
        
        # 2. Обработка Markdown-разметки
        result = self.PATTERNS["markdown_links"].sub(r'\1', result)
        result = self.PATTERNS["markdown_bold"].sub(r'\1', result)
        result = self.PATTERNS["markdown_italic"].sub(r'\1', result)
        
        # 3. Нормализация дозировок: 2,5 мг → 2.5 мг (для консистентности)
        if self.normalize_dosages:
            result = self.PATTERNS["dosage_range"].sub(r'\1.\2', result)
        
        # 4. Удаление эмодзи (если не нужны)
        if not self.keep_emojis and not preserve_structure:
            result = self.PATTERNS["emoji_cleanup"].sub('', result)
        
        # 5. Очистка от служебных пометок
        result = re.sub(r'\[Протокол не предусматривает[^\]]*\]', '', result, flags=re.IGNORECASE)
        
        return result.strip()
    
    @staticmethod
    def extract_plain_text(markdown: str) -> str:
        """Извлекает чистый текст из Markdown (удаляет все заголовки, списки)"""
        text = markdown
        # Удаляем заголовки
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Удаляем маркеры списков
        text = re.sub(r'^[\-\*\+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
        return text.strip()

