# src/preprocessing/medication_extractor.py
import re
from typing import List, Optional
from src.models.chunk import Medication

class MedicationExtractor:
    PATTERNS = {
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
    
    @classmethod
    def extract(cls, text: str) -> List[Medication]:
        if not text:
            return []
        meds, seen = [], set()
        for pat_name, pat in cls.PATTERNS.items():
            for m in pat.finditer(text):
                try:
                    name = m.group(1).strip()
                    if name.lower() in cls.FALSE_POSITIVES or len(name) < 4:
                        continue
                    dosage = m.group(2).strip() if m.lastindex >= 2 else None
                    key = f"{name.lower()}:{dosage}"
                    if key not in seen:
                        seen.add(key)
                        meds.append(Medication(name=name, dosage=dosage, route=None))
                except (IndexError, AttributeError):
                    continue
        return meds
    
    @classmethod
    def extract_keywords(cls, text: str, min_length: int = 3) -> List[str]:
        medical_suffixes = ['ит', 'оз', 'патия', 'алгия', 'емия', 'ургия', 'эктомия', 'томия']
        keywords = []
        words = re.findall(r'\b[А-ЯЁ][а-яё]{%d,}\b' % (min_length-1), text)
        for word in words:
            if any(word.lower().endswith(suf) for suf in medical_suffixes):
                keywords.append(word)
        common_terms = ['артериальная', 'гипертензия', 'инфаркт', 'стенокардия', 'тахикардия', 'брадикардия', 'антикоагулянт', 'антиагрегант']
        for term in common_terms:
            if term in text.lower():
                keywords.append(term.capitalize())
        return list(set(keywords))[:10]
