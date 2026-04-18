# src/preprocessing/medication_extractor.py
import re
from typing import List, Optional
from src.models.chunk import Medication

class MedicationExtractor:
    """Извлекает информацию о препаратах из медицинского текста"""
    
    # Паттерны для поиска препаратов (можно расширять)
    PATTERNS = {
        # "Название препарата — дозировка способ"
        "standard": re.compile(
            r'([А-ЯЁ][а-яё\-]+(?:\s+[А-ЯЁ][а-яё\-]+)*)\s*'  # Название (1-2 слова с заглавной)
            r'—?\s*'  # тире или пробел
            r'([\d.,\s\-]+(?:мг|мл|г|мкг|МЕ|%)?)\s*'  # Дозировка
            r'((?:внутривенно|в/в|внутримышечно|в/м|per\s*os|подкожно|местно|ректально)?).*?',  # Способ
            re.IGNORECASE
        ),
        # "Препарат (дозировка)"
        "parentheses": re.compile(
            r'([А-ЯЁ][а-яё\-]+)\s*\(([\d.,\s\-]+\s*(?:мг|мл|г))\)',
            re.IGNORECASE
        ),
        # Списки: "- Название: дозировка"
        "list_item": re.compile(
            r'^[\-\*\+]\s*([А-ЯЁ][а-яё\-]+)\s*[:\-]?\s*([\d.,\s\-]+\s*(?:мг|мл|г|мкг))?.*$',
            re.MULTILINE | re.IGNORECASE
        )
    }
    
    ROUTE_MAPPING = {
        "внутривенно": "в/в", "в/в": "в/в", "iv": "в/в",
        "внутримышечно": "в/м", "в/м": "в/м", "im": "в/м",
        "per os": "per os", "перорально": "per os", "внутрь": "per os",
        "подкожно": "п/к", "местно": "топически", "ректально": "ректально"
    }
    
    @classmethod
    def extract(cls, text: str) -> List[Medication]:
        """Извлекает список препаратов из текста"""
        if not text:
            return []
        
        medications = []
        seen = set()  # Для дедупликации
        
        # Пробуем разные паттерны
        for pattern_name, pattern in cls.PATTERNS.items():
            for match in pattern.finditer(text):
                try:
                    name = match.group(1).strip()
                    dosage = match.group(2).strip() if match.lastindex >= 2 else None
                    route_raw = match.group(3).strip() if match.lastindex >= 3 else ""
                    
                    # Нормализация способа введения
                    route = None
                    for key, value in cls.ROUTE_MAPPING.items():
                        if key.lower() in route_raw.lower():
                            route = value
                            break
                    
                    # Уникальный ключ для дедупликации
                    key = f"{name.lower()}:{dosage}:{route}"
                    if key not in seen:
                        seen.add(key)
                        medications.append(Medication(
                            name=name,
                            dosage=dosage,
                            route=route,
                            notes=f"extracted_via:{pattern_name}" if len(medications) > 5 else None
                        ))
                except (IndexError, AttributeError):
                    continue
        
        return medications
    
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

