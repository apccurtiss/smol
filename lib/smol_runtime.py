from pathlib import Path

from lib.smol_cache import cache


def list_files(filepath: str, origin: Path):
    def parse_file(filepath):
        return {
            'url': str(filepath),
            **cache.get(filepath, dependancy=origin).headers
        }

    return [parse_file(f) for f in origin.joinpath(filepath).glob('*') if f.is_file()]


def split(s: str, delim: str):
    return s.split(delim)


def build_runtime(filepath: Path):
    return {
        'list_files': lambda relpath: list_files(relpath, filepath),
        'split': split
    }