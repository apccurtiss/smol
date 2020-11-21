from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import re
from typing import Dict, Optional, Set, Tuple


@dataclass
class SmolFile:
    path: str
    content: str
    updated: datetime = field(default_factory=datetime.now)
    headers: Dict[str, str] = field(default_factory=dict)
    dependancies: Set['SmolFile'] = field(default_factory=set)


class SmolFileCache:
    '''Caches files and headers, and remembers things like dependancies and update times.'''
    cache = {}

    def __contains__(self, other):
        return other in self.cache.keys()

    def _parse_headers(self, text: str) -> Tuple(Dict[str, str], int):
        '''Parse headers and return the index where they end.'''
        headers = {}
        end = 0
        for match in re.finditer(r'\s*<!--\s*(.+?)\s*:\s*(.+?)\s*-->\s*', text):
            if not match.group(1):
                break

            headers[match.group(1)] = match.group(2)
            end = match.end()

        return headers, end

    def _load(self, filepath: Path, **attributes) -> SmolFile:
        '''Read headers and content from a file.'''
        if filepath.suffix in ['.html']:
            content = filepath.read_text()

            headers, end = self._parse_headers(content)
            # Separate content from headers.
            content = content[end:]
            return SmolFile(path=filepath, content=content, headers=headers, **attributes)

        else:
            filepath.read_bytes()

            return SmolFile(path=filepath, content=content, **attributes)

    def get(self,
        filepath: Path,
        dependancy: Optional[Path]=None,
        invalidate: bool=False)-> SmolFile:
        '''Return a file. Loads it into the cache if it's not there already.
        
        Params:
            filepath: The file to return.
            dependancy: Another file that depends on this one. This will be recorded, so if this
                file changes we can update the dependancy as well.
            invalidate: Re-load this file, even if it already exists in the cache.
        '''
        if invalidate or filepath not in self.cache:
            old_dependancies = self.cache[filepath].dependancies
            self.cache[filepath] = self._load(filepath, dependancies=old_dependancies)

        if dependancy is not None:
            self.cache[filepath].dependancies.add(dependancy)

        return self.cache[filepath]

cache = SmolFileCache()