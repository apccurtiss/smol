from pathlib import Path
import unittest

from lib.smol_runtime import build_runtime
from lib.smol_cache import SmolFileCache


class TestRuntime(unittest.TestCase):
    runtime = build_runtime(Path('test_files'))

    def test_split(self):
        split_fn = self.runtime['split']

        self.assertListEqual(split_fn('foo,bar,', ','), ['foo', 'bar', ''])
        self.assertListEqual(split_fn('foo', 'bar'), ['foo'])
    
    def test_list_files_uses_relative_path(self):
        list_files_fn = self.runtime['list_files']

        # We set the root path to be /test_files on creation, so it should list from there
        self.assertListEqual(list_files_fn('.'), ['index.html'])
        self.assertListEqual(list_files_fn('posts'), ['post_1.html', 'post_2.html'])
        self.assertListEqual(list_files_fn('../test_files/posts'), ['post_1.html', 'post_2.html'])
    
    def test_list_files_cannot_escape_project_root(self):
        list_files_fn = self.runtime['list_files']

        self.assertRaises(Exception, list_files_fn, '../..')