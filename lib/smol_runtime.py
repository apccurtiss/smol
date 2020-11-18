import os

from lib.smol_ast import SmolFn, SmolList, SmolStr

def list_files(path_obj):
    if not isinstance(path_obj, SmolStr):
        raise Exception('list_files requires a filepath')

    path = path_obj.value
    dirname = os.path.dirname(path)
    fullpath = os.path.join(dirname, path)
    _, _, filenames = os.walk(fullpath).__next__()

    return SmolList([SmolStr(os.path.join(dirname, filename)) for filename in filenames])

runtime = {
    'list_files': SmolFn(fn=list_files)
}