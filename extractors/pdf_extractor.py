# -*- coding: utf-8 -*-
"""
Экстрактор для PDF файлов клинических протоколов.
"""

import re
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base_extractor import BaseExtractor, ClinicalChunk


class PDFExtractor(BaseExtractor):
    """Экстрактор для PDF файлов."""

    def __init__(self):
        self.medication_patterns = [
            # Паттерн для препаратов с дозировкой: "Верапамил 0,25% раствор 2-4 мл (5-10 мг)"
            r'([А-Яа-яЁё]+(?:[-\s]?[А-Яа-яЁё]+)*)\s+(\d+(?:[.,]\d+)?%?\s*(?:раствор|таблетки?|капсулы?|инъекции?)?\s*(?:\d+(?:[.,]\d+)?\s*(?:мл|мг|г|мкг|ед\.|%)?)?)\s*(?:\((\d+(?:[.,]\d+)?(?:\s*-\s*\d+(?:[.,]\d+)?)?\s*(?:мг|мл|г|мкг))\))?',
        ]

        self.icd_pattern = r'([А-Я]\d{2}(?:\.\d{1,2})?)'
        self.diagnosis_header_pattern = r'(?:Наджелудочковая tachycardia|Тахикардия|Аритмия|Фибрилляция)'

    def extract(self, file_path: str) -> List[ClinicalChunk]:
        """Извлечение фрагментов из PDF файла."""
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("Установите pdfplumber: pip install pdfplumber")

        chunks = []
        full_text = ""

        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    full_text += f"\n--- Страница {page_num} ---\n{text}"

        return self.extract_from_text(full_text, Path(file_path).name)

    def extract_from_text(self, text: str, source_file: str = "") -> List[ClinicalChunk]:
        """Извлечение структурированных фрагментов из текста."""
        chunks = []

        # Извлечение диагнозов и кодов МКБ
        diagnoses = self._extract_diagnoses(text)

        # Извлечение диагностических процедур
        diagnostic_chunks = self._extract_diagnostic_procedures(text, diagnoses, source_file)
        chunks.extend(diagnostic_chunks)

        # Извлечение протоколов лечения (купирование приступа)
        emergency_chunks = self._extract_emergency_treatment(text, diagnoses, source_file)
        chunks.extend(emergency_chunks)

        # Извлечение профилактики приступов
        prophylaxis_chunks = self._extract_prophylaxis(text, diagnoses, source_file)
        chunks.extend(prophylaxis_chunks)

        # Извлечение препаратов с полной информацией
        medication_chunks = self._extract_medications(text, diagnoses, source_file)
        chunks.extend(medication_chunks)

        return chunks

    def _extract_diagnoses(self, text: str) -> List[Dict[str, str]]:
        """Извлечение диагнозов с кодами МКБ."""
        diagnoses = []

        # Паттерны для диагнозов
        patterns = [
            r'\*\*([А-Яа-яЁё\s\-]+?)\s*\(([A-Z]\d{2}(?:\.\d{1,2})?)\)\*\*',
            r'([А-Яа-яЁё\s\-]+?)\s*\(([A-Z]\d{2}(?:\.\d{1,2})?)\)',
            r'Нозологическая форма[:\s]+([А-Яа-яЁё\s\-]+)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                diagnosis = match.group(1).strip()
                icd_code = match.group(2).strip()

                if diagnosis and icd_code and len(diagnosis) > 3:
                    diagnoses.append({
                        "diagnosis": diagnosis,
                        "icd_code": icd_code
                    })

        return diagnoses

    def _extract_diagnostic_procedures(self, text: str, diagnoses: List[Dict[str, str]], source_file: str) -> List[ClinicalChunk]:
        """Извлечение диагностических процедур."""
        chunks = []

        # Поиск секции диагностики
        diag_pattern = r'(?:Диагностика|Обследование)[:\s]*(.*?)(?=(?:Лечение|Prophylaxis|Купирование|$))'
        matches = re.finditer(diag_pattern, text, re.IGNORECASE | re.DOTALL)

        for match in matches:
            section_text = match.group(1)
            procedures = self._parse_procedures(section_text)

            for diag in diagnoses:
                chunk = ClinicalChunk(
                    chunk_id=str(uuid.uuid4()),
                    diagnosis=diag["diagnosis"],
                    icd_code=diag["icd_code"],
                    section_type="diagnosis",
                    title=f"Диагностика: {diag['diagnosis']}",
                    content=section_text.strip(),
                    procedures=procedures,
                    source_file=source_file
                )
                chunks.append(chunk)

        return chunks

    def _extract_emergency_treatment(self, text: str, diagnoses: List[Dict[str, str]], source_file: str) -> List[ClinicalChunk]:
        """Извлечение протоколов купирования приступа."""
        chunks = []

        # Поиск секции купирования
        emergency_pattern = r'(?:Купирование\s+(?:приступа|пароксизма)|Экстренная\s+терапия)[:\s]*(.*?)(?=(?:Профилактика|Disclaimer|$))'
        matches = re.finditer(emergency_pattern, text, re.IGNORECASE | re.DOTALL)

        for match in matches:
            section_text = match.group(1)
            medications = self._extract_medication_list(section_text)
            contraindications = self._extract_contraindications(section_text)

            for diag in diagnoses:
                chunk = ClinicalChunk(
                    chunk_id=str(uuid.uuid4()),
                    diagnosis=diag["diagnosis"],
                    icd_code=diag["icd_code"],
                    section_type="emergency",
                    title=f"Купирование приступа: {diag['diagnosis']}",
                    content=section_text.strip(),
                    medications=medications,
                    contraindications=contraindications,
                    source_file=source_file
                )
                chunks.append(chunk)

        return chunks

    def _extract_prophylaxis(self, text: str, diagnoses: List[Dict[str, str]], source_file: str) -> List[ClinicalChunk]:
        """Извлечение протоколов профилактики."""
        chunks = []

        # Поиск секции профилактики
        proph_pattern = r'(?:Профилактика[^(]*|Поддерживающая\s+терапия)[:\s]*(.*?)(?=(?:Купирование|ЭИТ|Disclaimer|$))'
        matches = re.finditer(proph_pattern, text, re.IGNORECASE | re.DOTALL)

        for match in matches:
            section_text = match.group(1)
            medications = self._extract_medication_list(section_text)
            monitoring = self._extract_monitoring(section_text)

            for diag in diagnoses:
                chunk = ClinicalChunk(
                    chunk_id=str(uuid.uuid4()),
                    diagnosis=diag["diagnosis"],
                    icd_code=diag["icd_code"],
                    section_type="prophylaxis",
                    title=f"Профилактика: {diag['diagnosis']}",
                    content=section_text.strip(),
                    medications=medications,
                    monitoring=monitoring,
                    source_file=source_file
                )
                chunks.append(chunk)

        return chunks

    def _extract_medications(self, text: str, diagnoses: List[Dict[str, str]], source_file: str) -> List[ClinicalChunk]:
        """Извлечение информации о каждом препарате."""
        chunks = []

        # Паттерны для препаратов
        med_patterns = [
            # "Верапамил 0,25% раствор 2-4 мл (5-10 мг) внутривенно"
            r'\*?([А-Яа-яЁё][А-Яа-яЁё\s\-]{2,50}?)\s*(\d+(?:[.,]\d+)?%?\s*(?:раствор|таблетки?|капсулы?|инъекции?|ампулы?)?\s*(?:\d+(?:[.,]\d+)?\s*(?:мл|мг|г|мкг|ед\.)?)?)\s*(?:\((\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?\s*(?:мг|мл|г|мкг))\))?\s*(внутривенно|внутрь|перорально|подкожно|внутримышечно|сублингвально)?',
        ]

        for pattern in med_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                med_name = match.group(1).strip()
                dosage_form = match.group(2).strip() if match.group(2) else ""
                dosage = match.group(3).strip() if match.group(3) else ""
                route = match.group(4).strip() if match.group(4) else "внутрь"

                # Валидация названия препарата
                if len(med_name) > 2 and med_name not in ['при', 'для', 'примечание', 'лечение']:
                    medication_data = {
                        "name": med_name,
                        "dosage_form": dosage_form,
                        "dosage": dosage,
                        "route": route
                    }

                    for diag in diagnoses:
                        chunk = ClinicalChunk(
                            chunk_id=str(uuid.uuid4()),
                            diagnosis=diag["diagnosis"],
                            icd_code=diag["icd_code"],
                            section_type="treatment",
                            title=f"{med_name}: {dosage} {route}",
                            content=f"{med_name} {dosage_form} {dosage} {route}".strip(),
                            medications=[medication_data],
                            source_file=source_file
                        )
                        chunks.append(chunk)

        return chunks

    def _parse_procedures(self, text: str) -> List[str]:
        """Парсинг списка процедур."""
        procedures = []

        # Разбиение по точкам, запятым и номерам
        items = re.split(r'[;\n]|(?:\d+\.)', text)

        for item in items:
            item = item.strip()
            # Фильтрация значимых процедур
            if item and len(item) > 5:
                # Убираем маркеры обязательности
                item = re.sub(r'\*\*Обязательная\*\*:?|Обязательная:?', '', item)
                item = re.sub(r'\*\*Дополнительная\*\*:?|Дополнительная:?', '', item)
                item = item.strip()
                if item:
                    procedures.append(item)

        return procedures[:20]  # Ограничиваем количество

    def _extract_medication_list(self, text: str) -> List[Dict[str, Any]]:
        """Извлечение списка препаратов из текста."""
        medications = []

        # Паттерн для извлечения препаратов
        med_pattern = r'\*?([А-Яа-яЁё][А-Яа-яЁё\s\-]{2,30}?)\s*(\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?)\s*(мг|мл|г|мкг|ед\.)/(?:сут\.|кг|час)'
        matches = re.finditer(med_pattern, text)

        for match in matches:
            medications.append({
                "name": match.group(1).strip(),
                "dosage": match.group(2).strip(),
                "unit": match.group(3).strip()
            })

        return medications

    def _extract_contraindications(self, text: str) -> List[str]:
        """Извлечение противопоказаний."""
        contraindications = []

        # Поиск секции противопоказаний
        contra_pattern = r'(?:противопоказан[а-я]*|противопоказания|нельзя назначать)[:\s]*(.*?)(?:\.|$)'
        matches = re.finditer(contra_pattern, text, re.IGNORECASE | re.DOTALL)

        for match in matches:
            section = match.group(1)
            # Извлечение конкретных противопоказаний
            items = re.split(r'(?:,|и\s)', section)
            for item in items:
                item = item.strip()
                if item and len(item) > 3:
                    contraindications.append(item)

        return contraindications

    def _extract_monitoring(self, text: str) -> List[str]:
        """Извлечение параметров мониторинга."""
        monitoring = []

        # Паттерны для мониторинга
        monitor_patterns = [
            r'контроль\s+([\w\s]+?)(?:,|не\s+реже|$)',
            r'(?:не\s+реже|каждые)\s+(\d+\s*(?:месяц|недел|день|год))',
        ]

        for pattern in monitor_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                item = match.group(0).strip()
                if item and len(item) > 5:
                    monitoring.append(item)

        return list(set(monitoring))  # Убираем дубликаты
