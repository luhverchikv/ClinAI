from pathlib import Path
from typing import Iterator, Tuple
import logging
logger = logging.getLogger(__name__)

class FileLoader:
    def __init__(self, directory: str, encoding: str = "utf-8"):
        self.directory = Path(directory)
        self.encoding = encoding
    def validate_directory(self) -> bool:
        if not self.directory.exists(): logger.error(f"Dir not found: {self.directory}"); return False
        if not self.directory.is_dir(): logger.error(f"Not a dir: {self.directory}"); return False
        return True
    def list_files(self) -> Iterator[Path]:
        if not self.validate_directory(): return
        for ext in [".md", ".markdown"]: yield from self.directory.rglob(f"*{ext}")
    def read_file(self, file_path: Path) -> Tuple[str, str]:
        return file_path.name, file_path.read_text(encoding=self.encoding)