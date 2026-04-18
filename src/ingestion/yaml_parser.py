import re
import yaml
import frontmatter
import logging
logger = logging.getLogger(__name__)

class YAMLParseError(Exception): pass

class YAMLParser:
    @staticmethod
    def extract_frontmatter(content: str) -> tuple[dict, str]:
        try:
            post = frontmatter.loads(content)
            return dict(post.metadata), post.content
        except Exception as e:
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if match:
                return yaml.safe_load(match.group(1)), content[match.end():]
            raise YAMLParseError(f"Frontmatter missing or invalid: {e}")
    @staticmethod
    def parse_sections(body: str) -> dict[str, str]:
        sections = {}
        for m in re.finditer(r"##\s+([^\n]+)\n(.*?)(?=\n##\s+|$)", body, re.DOTALL):
            sections[m.group(1).strip()] = m.group(2).strip()
        return sections