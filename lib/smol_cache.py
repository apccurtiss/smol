from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import re
from typing import Dict


@dataclass
class SmolFile:
    path: str
    content: str
    updated: datetime = field(default_factory=datetime.now)
    headers: Dict[str, str] = field(default_factory=dict)


class SmolFileCache:
    cache = {}

    def _parse_headers(self, text: str):
        """Parse headers and return the index where they end."""
        headers = {}
        end = 0
        for match in re.finditer(r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*', text):
            if not match.group(1):
                break

            headers[match.group(1)] = match.group(2)
            end = match.end()

        return headers, end

    def _load(self, filepath: Path):
        """Read headers and content from a file."""
        if filepath.suffix in ['.html']:
            content = filepath.read_text()

            headers, end = self._parse_headers(content)
            # Separate content from headers.
            content = content[end:]
            return SmolFile(path=filepath, content=content, headers=headers)

        else:
            filepath.read_bytes()

            return SmolFile(path=filepath, content=content)

    def get(self, filepath, invalidate=False):
        if invalidate or filepath not in self.cache:
            self.cache[filepath] = self._load(filepath)

        return self.cache[filepath]

cache = SmolFileCache()