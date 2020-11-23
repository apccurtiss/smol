from pathlib import Path

from lib.smol_cache import cache


def list_files(filepath: str, root: Path, origin: Path):
    def build_return(filepath):
        return {
            'url': filepath.resolve().relative_to(root.resolve()),
            **cache.get(filepath, dependancy=origin).headers
        }

    searchpath = origin.parent.joinpath(filepath)
    return [build_return(f) for f in searchpath.glob('*') if f.is_file()]


def split(s: str, delim: str):
    return s.split(delim)


def build_runtime(basepath: Path, root: Path):
    return {
        'list_files': lambda relpath: list_files(relpath, root, basepath),
        'split': split
    }