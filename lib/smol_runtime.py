import os

from lib.smol_ast import SmolFn, SmolList, SmolObj, SmolStr
from lib.smol_cache import cache

def list_files(filepath, _params, list_path):
    if not isinstance(list_path, SmolStr):
        raise Exception('list_files requires a filepath')

    fullpath = os.path.join(os.path.dirname(filepath), list_path.value)
    _, _, filenames = os.walk(fullpath).__next__()

    def build_file_object(filename):
        cache_obj = cache.get(os.path.join(fullpath, filename))
        return SmolObj({
            'url': SmolStr(cache_obj.path),
            **cache_obj.headers
        })

    return SmolList([build_file_object(filename) for filename in filenames])

def split(filepath, _params, string, delim):
    return SmolList([SmolStr(chunk) for chunk in string.value.split(delim.value)])

runtime = {
    'list_files': SmolFn(fn=list_files),
    'split': SmolFn(fn=split)
}