# -*- coding: utf-8 -*-
"""
Поисковая система для RAG на основе извлечённых клинических протоколов.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

try:
    from rank_bm25 import BM25Ranking
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


@dataclass
class SearchResult:
    """Результат поиска."""
    chunk_id: str
    diagnosis: str
    icd_code: str
    section_type: str
    title: str
    content: str
    medications: List[Dict[str, Any]]
    contraindications: List[str]
    score: float
    source_file: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "diagnosis": self.diagnosis,
            "icd_code": self.icd_code,
            "section_type": self.section_type,
            "title": self.title,
            "content": self.content,
            "medications": self.medications,
            "contraindications": self.contraindications,
            "score": round(self.score, 4),
            "source_file": self.source_file
        }


class ClinicalSearchEngine:
    """Поисковая система для клинических протоколов."""

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self._indexed = False

    def load_from_json(self, json_path: str):
        """Загрузка фрагментов из JSON."""
        with open(json_path, 'r', encoding='utf-8') as f:
            self.chunks = json.load(f)
        self._indexed = True
        print(f"Загружено фрагментов: {len(self.chunks)}")

    def load_from_directory(self, directory: str):
        """Загрузка всех JSON файлов из директории."""
        path = Path(directory)
        for json_file in path.glob("*.json"):
            with open(json_file, 'r', encoding='utf-8') as f:
                self.chunks.extend(json.load(f))
        self._indexed = True
        print(f"Загружено фрагментов: {len(self.chunks)}")

    def search(self, query: str, top_k: int = 5, section_filter: str = None) -> List[SearchResult]:
        """
        Поиск по запросу.

        Args:
            query: Поисковый запрос (диагноз, симптомы, название препарата)
            top_k: Количество результатов
            section_filter: Фильтр по типу раздела (diagnosis, emergency, prophylaxis, treatment)
        """
        if not self._indexed:
            raise RuntimeError("Сначала загрузите данные через load_from_json()")

        # Токенизация запроса
        query_tokens = self._tokenize(query)

        # Фильтрация по секции
        filtered_chunks = self.chunks
        if section_filter:
            filtered_chunks = [c for c in filtered_chunks if c.get('section_type') == section_filter]

        # Вычисление релевантности
        results = []
        for chunk in filtered_chunks:
            score = self._calculate_relevance(query_tokens, chunk)

            if score > 0.1:  # Порог релевантности
                results.append(SearchResult(
                    chunk_id=chunk.get('chunk_id', ''),
                    diagnosis=chunk.get('diagnosis', ''),
                    icd_code=chunk.get('icd_code', ''),
                    section_type=chunk.get('section_type', ''),
                    title=chunk.get('title', ''),
                    content=chunk.get('content', ''),
                    medications=chunk.get('medications', []),
                    contraindications=chunk.get('contraindications', []),
                    score=score,
                    source_file=chunk.get('source_file', '')
                ))

        # Сортировка по релевантности
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    def search_by_icd(self, icd_code: str, top_k: int = 10) -> List[SearchResult]:
        """Поиск по коду МКБ."""
        if not self._indexed:
            raise RuntimeError("Сначала загрузите данные через load_from_json()")

        results = []
        for chunk in self.chunks:
            if chunk.get('icd_code', '').upper() == icd_code.upper():
                results.append(SearchResult(
                    chunk_id=chunk.get('chunk_id', ''),
                    diagnosis=chunk.get('diagnosis', ''),
                    icd_code=chunk.get('icd_code', ''),
                    section_type=chunk.get('section_type', ''),
                    title=chunk.get('title', ''),
                    content=chunk.get('content', ''),
                    medications=chunk.get('medications', []),
                    contraindications=chunk.get('contraindications', []),
                    score=1.0,
                    source_file=chunk.get('source_file', '')
                ))

        return results[:top_k]

    def search_medications(self, medication_name: str, top_k: int = 10) -> List[SearchResult]:
        """Поиск по названию препарата."""
        if not self._indexed:
            raise RuntimeError("Сначала загрузите данные через load_from_json()")

        med_lower = medication_name.lower()
        results = []

        for chunk in self.chunks:
            medications = chunk.get('medications', [])
            for med in medications:
                med_name = med.get('name', '').lower()
                if med_lower in med_name or med_name in med_lower:
                    results.append(SearchResult(
                        chunk_id=chunk.get('chunk_id', ''),
                        diagnosis=chunk.get('diagnosis', ''),
                        icd_code=chunk.get('icd_code', ''),
                        section_type=chunk.get('section_type', ''),
                        title=chunk.get('title', ''),
                        content=chunk.get('content', ''),
                        medications=medications,
                        contraindications=chunk.get('contraindications', []),
                        score=1.0,
                        source_file=chunk.get('source_file', '')
                    ))
                    break

        return results[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """Токенизация текста."""
        import re
        # Удаление пунктуации и приведение к нижнему регистру
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        tokens = text.split()
        # Удаление стоп-слов
        stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'при', 'не', 'что', 'как', 'это'}
        tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
        return tokens

    def _calculate_relevance(self, query_tokens: List[str], chunk: Dict[str, Any]) -> float:
        """Вычисление релевантности через TF-IDF подход."""
        # Получение текста chunk
        chunk_text = chunk.get('content', '') + ' ' + chunk.get('title', '') + ' ' + chunk.get('diagnosis', '')
        chunk_tokens = self._tokenize(chunk_text)

        if not query_tokens or not chunk_tokens:
            return 0.0

        # Подсчёт совпадений
        matches = 0
        for q_token in query_tokens:
            for c_token in chunk_tokens:
                # Частичное совпадение для морфологии
                if q_token in c_token or c_token in q_token:
                    matches += 1
                    break

        # Нормализация
        return matches / len(query_tokens)

    def format_results(self, results: List[SearchResult]) -> str:
        """Форматирование результатов для отображения врачу."""
        if not results:
            return "Результаты не найдены."

        output = []
        output.append(f"📋 Найдено рекомендаций: {len(results)}\n")
        output.append("=" * 60 + "\n")

        for i, result in enumerate(results, 1):
            section_emoji = {
                "diagnosis": "🔬",
                "emergency": "🚨",
                "prophylaxis": "💊",
                "treatment": "💉"
            }.get(result.section_type, "📋")

            section_name = {
                "diagnosis": "Диагностика",
                "emergency": "Неотложная помощь",
                "prophylaxis": "Профилактика",
                "treatment": "Лечение"
            }.get(result.section_type, result.section_type)

            output.append(f"{i}. {section_emoji} {result.title}\n")
            output.append(f"   Диагноз: {result.diagnosis} ({result.icd_code})\n")
            output.append(f"   Раздел: {section_name}\n")
            output.append(f"   ───\n")

            # Контент (сокращённо)
            content_lines = result.content.split('\n')[:5]
            output.append(f"   {' '.join(content_lines)}\n")

            # Препараты
            if result.medications:
                output.append(f"   💊 Препараты:\n")
                for med in result.medications:
                    med_line = f"      • {med.get('name', '')}"
                    if med.get('dosage'):
                        med_line += f" — {med.get('dosage')}"
                    if med.get('route'):
                        med_line += f" ({med.get('route')})"
                    output.append(med_line + "\n")

            # Противопоказания
            if result.contraindications:
                output.append(f"   ⚠️ Противопоказания: {', '.join(result.contraindications)}\n")

            output.append(f"   Релевантность: {result.score:.0%}\n")
            output.append("-" * 60 + "\n")

        return ''.join(output)


def main():
    """CLI интерфейс поиска."""
    import argparse

    parser = argparse.ArgumentParser(description='Поиск в клинических протоколах')
    parser.add_argument('--data', required=True, help='Путь к JSON с данными')
    parser.add_argument('-q', '--query', help='Поисковый запрос')
    parser.add_argument('--icd', help='Код МКБ (например, I47.1)')
    parser.add_argument('--med', '--medication', dest='medication', help='Название препарата')
    parser.add_argument('-k', '--top-k', type=int, default=5, help='Количество результатов')
    parser.add_argument('--section', help='Фильтр по секции (diagnosis/emergency/prophylaxis/treatment)')

    args = parser.parse_args()

    engine = ClinicalSearchEngine()
    engine.load_from_json(args.data)

    results = []

    if args.query:
        results = engine.search(args.query, args.top_k, args.section)
    elif args.icd:
        results = engine.search_by_icd(args.icd, args.top_k)
    elif args.medication:
        results = engine.search_medications(args.medication, args.top_k)
    else:
        print("Укажите запрос: --query, --icd или --med")
        return

    print(engine.format_results(results))


if __name__ == '__main__':
    main()
