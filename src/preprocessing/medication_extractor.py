# src/preprocessing/medication_extractor.py
import re
from typing import List, Optional
from src.models.chunk import Medication

class MedicationExtractor:
    """Извлекает информацию о препаратах из медицинского текста"""
    
    # Паттерны для поиска препаратов (можно расширять)
    PATTERNS = {
        # Только если перед названием есть медицинский контекст или после идёт четкая дозировка с единицами
        "standard": re.compile(
            r'(?:назначают|вводят|рекомендуется|препарат|лекарство|терапия)\s+'
            r'([А-ЯЁ][а-яё\-]{2,}(?:\s+[А-ЯЁ][а-яё\-]{2,})*)\s*'
            r'(?:в\s+дозе\s+|—\s*|\()\s*'
            r'([\d.,\s\-]+\s*(?:мг|мл|г|мкг|МЕ|%))',
            re.IGNORECASE
        ),
        "parentheses": re.compile(
            r'([А-ЯЁ][а-яё\-]{3,})\s*\(([\d.,\s\-]+\s*(?:мг|мл|г|мкг))\)',
            re.IGNORECASE
        )
    }
    
    FALSE_POSITIVES = {"доза", "введение", "режим", "кратность", "способ", "путь", "время", "скорость"}

    ROUTE_MAPPING = {
        "внутривенно": "в/в", "в/в": "в/в", "iv": "в/в",
        "внутримышечно": "в/м", "в/м": "в/м", "im": "в/м",
        "per os": "per os", "перорально": "per os", "внутрь": "per os",
        "подкожно": "п/к", "местно": "топически", "ректально": "ректально"
    }
    
    
    @classmethod
    def extract(cls, text: str) -> List[Medication]:
    if not text: return []
    meds = []
    seen = set()
    
    for pat_name, pat in cls.PATTERNS.items():
        for m in pat.finditer(text):
            try:
                name = m.group(1).strip()
                # Пропускаем если имя в黑名单 или слишком короткое
                if name.lower() in cls.FALSE_POSITIVES or len(name) < 4:
                    continue
                
                dosage = m.group(2).strip() if m.lastindex >= 2 else None
                route = None  # Упрощаем, маршрут будем извлекать позже контекстно
                
                key = f"{name.lower()}:{dosage}"
                if key not in seen:
                    seen.add(key)
                    meds.append(Medication(name=name, dosage=dosage, route=route))
            except (IndexError, AttributeError):
                continue
    return meds

    
    @classmethod
    def extract_keywords(cls, text: str, min_length: int = 3) -> List[str]:
        """Извлекает ключевые медицинские термины"""
        # Простая эвристика: слова с заглавной буквы + медицинские суффиксы
        medical_suffixes = ['ит', 'оз', 'патия', 'алгия', 'емия', 'ургия', 'эктомия', 'томия']
        keywords = []
        
        words = re.findall(r'\b[А-ЯЁ][а-яё]{%d,}\b' % (min_length-1), text)
        for word in words:
            if any(word.lower().endswith(suf) for suf in medical_suffixes):
                keywords.append(word)
        
        # Добавляем частотные медицинские термины
        common_terms = ['артериальная', 'гипертензия', 'инфаркт', 'стенокардия', 
                       'тахикардия', 'брадикардия', 'антикоагулянт', 'антиагрегант']
        for term in common_terms:
            if term in text.lower():
                keywords.append(term.capitalize())
        
        return list(set(keywords))[:10]  # Ограничиваем количество

