from dataclasses import dataclass, field
from datetime import datetime
import os
import re
from typing import Dict

from lib.smol_ast import SmolStr

@dataclass
class SmolFile:
    path: str
    content: str
    updated: datetime = field(default_factory=datetime.now)
    headers: Dict[str, str] = field(default_factory=dict)
    is_html: bool = field(default=False)

class SmolFileCache:
    cache = {}

    def _parse_headers(self, text):
        """Parse headers and return the index where they end."""
        headers = {}
        end = 0
        for match in re.finditer(r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*', text):
            if not match.group(1):
                break

            headers[match.group(1)] = SmolStr(match.group(2))
            end = match.end()

        return headers, end

    def _load(self, filepath):
        """Read headers and content from a file."""
        if filepath.endswith('.html'):
            with open(filepath) as f:
                content = f.read()

            headers, end = self._parse_headers(content)
            # Separate content from headers.
            content = content[end:]
            return SmolFile(path=filepath, content=content, headers=headers, is_html=True)

        else:
            with open(filepath, 'rb') as f:
                content = f.read()

            return SmolFile(path=filepath, content=content)

    def get(self, filepath, invalidate=False):
        norm_filepath = os.path.normpath(filepath)

        if invalidate or norm_filepath not in self.cache:
            self.cache[norm_filepath] = self._load(norm_filepath)
        
        return self.cache[norm_filepath]

cache = SmolFileCache()